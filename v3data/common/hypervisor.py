import asyncio

from fastapi import Response, status

from v3data.common import ExecutionOrderWrapper
from v3data.hypervisor import HypervisorInfo
from v3data.toplevel import TopLevelData
from v3data.enums import Chain, Protocol
from v3data.hype_fees.fees import fees_all
from v3data.hype_fees.fees_yield import fee_returns_all
from v3data.hype_fees.impermanent_divergence import impermanent_divergence_all


from database.collection_endpoint import (
    db_returns_manager,
    db_allData_manager,
    db_aggregateStats_manager,
)
from v3data.config import MONGO_DB_URL

import logging

logger = logging.getLogger(__name__)


class AllData(ExecutionOrderWrapper):
    async def _database(self):
        _mngr = db_allData_manager(mongo_url=MONGO_DB_URL)
        result = await _mngr.get_data(chain=self.chain, protocol=self.protocol)
        self.database_datetime = result.pop("datetime", "")
        return result

    async def _subgraph(self):
        hypervisor_info = HypervisorInfo(self.protocol, self.chain)
        return await hypervisor_info.all_data()


class FeeReturns(ExecutionOrderWrapper):
    def __init__(
        self, protocol: Protocol, chain: Chain, days: int, response: Response = None
    ):
        self.days = days
        super().__init__(protocol, chain, response)

    async def _database(self):
        returns_manager = db_returns_manager(mongo_url=MONGO_DB_URL)
        result = await returns_manager.get_feeReturns(
            chain=self.chain, protocol=self.protocol, period=self.days
        )
        self.database_datetime = result.pop("datetime", "")
        return result

    async def _subgraph(self):
        return await fee_returns_all(self.protocol, self.chain, self.days)


class AggregateStats(ExecutionOrderWrapper):
    async def _database(self):
        _mngr = db_aggregateStats_manager(mongo_url=MONGO_DB_URL)
        result = await _mngr.get_data(chain=self.chain, protocol=self.protocol)
        self.database_datetime = result.pop("datetime", "")
        return result

    async def _subgraph(self):
        top_level = TopLevelData(self.protocol, self.chain)
        top_level_data = await top_level.all_stats()

        return {
            "totalValueLockedUSD": top_level_data["tvl"],
            "pairCount": top_level_data["hypervisor_count"],
            "totalFeesClaimedUSD": top_level_data["fees_claimed"],
        }


class HypervisorsReturnsAllPeriods(ExecutionOrderWrapper):
    def __init__(
        self,
        protocol: Protocol,
        chain: Chain,
        hypervisors: list[str] | None = None,
        response: Response = None,
    ):
        self.hypervisors = (
            [hypervisor.lower() for hypervisor in hypervisors] if hypervisors else None
        )
        super().__init__(protocol, chain, response)

    async def _database(self):
        average_returns_mngr = db_returns_manager(mongo_url=MONGO_DB_URL)

        av_result = await average_returns_mngr.get_hypervisors_returns_average(
            chain=self.chain, protocol=self.protocol
        )
        if len(av_result) < 0:
            raise Exception

            results_na = {"feeApr": 0, "feeApy": 0, "status": "unavailable on database"}

            result = dict()
            # CONVERT result so is equal to original
            for hypervisor in av_result:
                result[hypervisor["_id"]] = dict()
                try:
                    result[hypervisor["_id"]]["daily"] = {
                        "feeApr": hypervisor["returns"]["1"]["av_feeApr"],
                        "feeApy": hypervisor["returns"]["1"]["av_feeApy"],
                        "status": "database",
                    }
                except Exception:
                    result[hypervisor["_id"]]["daily"] = results_na
                try:
                    result[hypervisor["_id"]]["weekly"] = {
                        "feeApr": hypervisor["returns"]["7"]["av_feeApr"],
                        "feeApy": hypervisor["returns"]["7"]["av_feeApy"],
                        "status": "database",
                    }
                except Exception:
                    result[hypervisor["_id"]]["weekly"] = results_na
                try:
                    result[hypervisor["_id"]]["monthly"] = {
                        "feeApr": hypervisor["returns"]["30"]["av_feeApr"],
                        "feeApy": hypervisor["returns"]["30"]["av_feeApy"],
                        "status": "database",
                    }
                except Exception:
                    result[hypervisor["_id"]]["monthly"] = results_na
                try:
                    result[hypervisor["_id"]]["allTime"] = {
                        "feeApr": hypervisor["returns"]["30"]["av_feeApr"],
                        "feeApy": hypervisor["returns"]["30"]["av_feeApy"],
                        "status": "database",
                    }
                except Exception:
                    result[hypervisor["_id"]]["allTime"] = results_na

            return result

    async def _subgraph(self):
        daily, weekly, monthly = await asyncio.gather(
            fee_returns_all(self.protocol, self.chain, 1, self.hypervisors),
            fee_returns_all(self.protocol, self.chain, 7, self.hypervisors),
            fee_returns_all(self.protocol, self.chain, 30, self.hypervisors),
        )

        results = {}
        for hypervisor_id in daily.keys():
            hypervisor_daily = daily.get(hypervisor_id)
            hypervisor_weekly = weekly.get(hypervisor_id)
            hypervisor_monthly = monthly.get(hypervisor_id)

            symbol = hypervisor_daily.pop("symbol")
            hypervisor_weekly.pop("symbol")
            hypervisor_monthly.pop("symbol")

            if hypervisor_weekly["feeApr"] == 0:
                hypervisor_weekly = hypervisor_daily

            if hypervisor_monthly["feeApr"] == 0:
                hypervisor_monthly = hypervisor_weekly

            results[hypervisor_id] = {"symbol": symbol}
            results[hypervisor_id]["daily"] = hypervisor_daily
            results[hypervisor_id]["weekly"] = hypervisor_weekly
            results[hypervisor_id]["monthly"] = hypervisor_monthly
            results[hypervisor_id]["allTime"] = hypervisor_monthly

        return results


class ImpermanentDivergence(ExecutionOrderWrapper):
    def __init__(
        self, protocol: Protocol, chain: Chain, days: int, response: Response = None
    ):
        self.days = days
        super().__init__(protocol, chain, response)

    async def _database(self):
        # check days in database
        if not self.days in [1, 7, 30]:
            raise NotImplementedError(
                " Only a limited quantity of periods reside in database. Chosen one is not among them"
            )

    async def _subgraph(self):
        return await impermanent_divergence_all(self.protocol, self.chain, self.days)


async def hypervisor_basic_stats(
    protocol: Protocol, chain: Chain, hypervisor_address: str, response: Response
):
    hypervisor_info = HypervisorInfo(protocol, chain)
    basic_stats = await hypervisor_info.basic_stats(hypervisor_address)

    if basic_stats:
        return basic_stats
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return "Invalid hypervisor address or not enough data"


async def recent_fees(protocol: Protocol, chain: Chain, hours: int = 24):
    top_level = TopLevelData(protocol, chain)
    recent_fees = await top_level.recent_fees(hours)

    return {"periodHours": hours, "fees": recent_fees}


async def hypervisors_average_return(
    protocol: Protocol, chain: Chain, response: Response = None
):
    if response:
        response.headers["X-Database"] = "true"
    average_returns_mngr = db_returns_manager(mongo_url=MONGO_DB_URL)
    return await average_returns_mngr.get_hypervisors_average(
        chain=chain, protocol=protocol
    )


async def hypervisor_average_return(
    protocol: Protocol, chain: Chain, hypervisor_address: str, response: Response = None
):
    if response:
        response.headers["X-Database"] = "true"
    average_returns_mngr = db_returns_manager(mongo_url=MONGO_DB_URL)
    return await average_returns_mngr.get_hypervisor_average(
        chain=chain, hypervisor_address=hypervisor_address, protocol=protocol
    )


async def uncollected_fees(protocol: Protocol, chain: Chain, hypervisor_address: str):
    return await fees_all(protocol, chain, [hypervisor_address])


async def uncollected_fees_all(protocol: Protocol, chain: Chain):
    return await fees_all(protocol, chain)
