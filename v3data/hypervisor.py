import logging
import math
import numpy as np
from datetime import timedelta
from pandas import DataFrame

from v3data import GammaClient, UniswapV3Client
from v3data.utils import tick_to_priceDecimal, timestamp_ago, timestamp_to_date
from v3data.constants import DAYS_IN_PERIOD, SECONDS_IN_DAYS
from v3data.config import EXCLUDED_HYPERVISORS, FALLBACK_DAYS

DAY_SECONDS = 24 * 60 * 60
YEAR_SECONDS = 365 * DAY_SECONDS
X128 = math.pow(2, 128)

logger = logging.getLogger(__name__)


class HypervisorData:
    def __init__(self, chain: str = "mainnet"):
        self.chain = chain
        self.gamma_client = GammaClient(chain)
        self.uniswap_client = UniswapV3Client(chain)
        self.basics_data = {}
        self.pools_data = {}
        self.fees_data = {}

    async def get_rebalance_data(self, hypervisor_address, time_delta, limit=1000):
        query = """
        query rebalances($hypervisor: String!, $timestamp_start: Int!, $limit: Int!){
            uniswapV3Rebalances(
                first: $limit
                where: {
                    hypervisor: $hypervisor
                    timestamp_gte: $timestamp_start
                }
            ) {
                id
                hypervisor {id}
                timestamp
                grossFeesUSD
                protocolFeesUSD
                netFeesUSD
                totalAmountUSD
            }
        }
        """
        timestamp_start = timestamp_ago(time_delta)
        variables = {
            "hypervisor": hypervisor_address.lower(),
            "timestamp_start": timestamp_start,
            "limit": limit,
        }
        response = await self.gamma_client.query(query, variables)

        if hypervisor_address == "0x0ec4a47065bf52e1874d2491d4deeed3c638c75f":
            for rebalance in response["data"]["uniswapV3Rebalances"]:
                if (
                    rebalance["id"]
                    == "0x9144d5c6a7e8ffd335c837c5877397e96ea3abbc77c9598b07255add6db3fc13-15"
                ):
                    rebalance["grossFeesUSD"] = str(
                        float(rebalance["grossFeesUSD"]) * 0.08
                    )
                    rebalance["protocolFeesUSD"] = str(
                        float(rebalance["protocolFeesUSD"]) * 0.08
                    )
                    rebalance["netFeesUSD"] = str(float(rebalance["netFeesUSD"]) * 0.08)
                    rebalance["totalAmountUSD"] = str(
                        float(rebalance["totalAmountUSD"]) * 0.08
                    )

        return response["data"]["uniswapV3Rebalances"]

    async def _get_all_rebalance_data(self, time_delta):
        query = """
        query allRebalances($timestamp_start: Int!){
            uniswapV3Hypervisors(
                first: 1000
            ){
                id
                rebalances(
                    first: 1000
                    where: { timestamp_gte: $timestamp_start }
                    orderBy: timestamp
                    orderDirection: desc
                ) {
                    id
                    hypervisor {id}
                    timestamp
                    grossFeesUSD
                    protocolFeesUSD
                    netFeesUSD
                    totalAmountUSD
                }
            }
        }
        """
        variables = {"timestamp_start": timestamp_ago(time_delta)}
        response = await self.gamma_client.query(query, variables)

        for hypervisor in response["data"]["uniswapV3Hypervisors"]:
            if hypervisor["id"] == "0x0ec4a47065bf52e1874d2491d4deeed3c638c75f":
                for rebalance in hypervisor["rebalances"]:
                    if (
                        rebalance["id"]
                        == "0x9144d5c6a7e8ffd335c837c5877397e96ea3abbc77c9598b07255add6db3fc13-15"
                    ):
                        rebalance["grossFeesUSD"] = str(
                            float(rebalance["grossFeesUSD"]) * 0.08
                        )
                        rebalance["protocolFeesUSD"] = str(
                            float(rebalance["protocolFeesUSD"]) * 0.08
                        )
                        rebalance["netFeesUSD"] = str(
                            float(rebalance["netFeesUSD"]) * 0.08
                        )
                        rebalance["totalAmountUSD"] = str(
                            float(rebalance["totalAmountUSD"]) * 0.08
                        )

        self.all_rebalance_data = response["data"]["uniswapV3Hypervisors"]

    async def _get_hypervisor_data(self, hypervisor_address):
        query = """
        query hypervisor($id: String!){
            uniswapV3Hypervisor(
                id: $id
            ) {
                id
                created
                baseLower
                baseUpper
                totalSupply
                maxTotalSupply
                deposit0Max
                deposit1Max
                grossFeesClaimed0
                grossFeesClaimed1
                grossFeesClaimedUSD
                feesReinvested0
                feesReinvested1
                feesReinvestedUSD
                tvl0
                tvl1
                tvlUSD
                pool{
                    id
                    fee
                    token0{
                        symbol
                        decimals
                    }
                    token1{
                        symbol
                        decimals
                    }
                }
            }
        }
        """
        variables = {"id": hypervisor_address.lower()}
        response = await self.gamma_client.query(query, variables)

        if hypervisor_address == "0x0ec4a47065bf52e1874d2491d4deeed3c638c75f":
            response["data"]["uniswapV3Hypervisor"]["grossFeesClaimedUSD"] = str(
                float(response["data"]["uniswapV3Hypervisor"]["grossFeesClaimedUSD"])
                - 238300
            )
            response["data"]["uniswapV3Hypervisor"]["feesReinvestedUSD"] = str(
                float(response["data"]["uniswapV3Hypervisor"]["feesReinvestedUSD"])
                - 214470
            )

        return response["data"]["uniswapV3Hypervisor"]

    async def _get_all_data(self):
        query_basics = """
        {
            uniswapV3Hypervisors(
                first:1000
            ){
                id
                created
                baseLower
                baseUpper
                totalSupply
                maxTotalSupply
                deposit0Max
                deposit1Max
                grossFeesClaimed0
                grossFeesClaimed1
                grossFeesClaimedUSD
                feesReinvested0
                feesReinvested1
                feesReinvestedUSD
                tvl0
                tvl1
                tvlUSD
                pool{
                    id
                    fee
                    token0{
                        symbol
                        decimals
                    }
                    token1{
                        symbol
                        decimals
                    }
                }
            }
        }
        """

        basics_response = await self.gamma_client.query(query_basics)

        for hypervisor in basics_response["data"]["uniswapV3Hypervisors"]:
            if hypervisor["id"] == "0x0ec4a47065bf52e1874d2491d4deeed3c638c75f":
                hypervisor["grossFeesClaimedUSD"] = str(
                    float(hypervisor["grossFeesClaimedUSD"]) - 238300
                )
                hypervisor["feesReinvestedUSD"] = str(
                    float(hypervisor["feesReinvestedUSD"]) - 214470
                )

        basics = basics_response["data"]["uniswapV3Hypervisors"]
        pool_addresses = [hypervisor["pool"]["id"] for hypervisor in basics]

        query_pool = """
        query slot0($pools: [String!]!){
            pools(
                where: {
                    id_in: $pools
                }
            ) {
                id
                sqrtPrice
                tick
                observationIndex
                feesUSD
                totalValueLockedUSD
            }
        }
        """
        variables = {"pools": pool_addresses}
        pools_response = await self.uniswap_client.query(query_pool, variables)
        pools_data = pools_response["data"]["pools"]
        pools = {pool.pop("id"): pool for pool in pools_data}

        self.basics_data = basics
        self.pools_data = pools

    async def _get_uncollected_fees_data(self, hypervisor_address):
        hypervisor_query = """
        query hypervisor($id: String!){
            uniswapV3Hypervisor(
                id: $id
            ){
                id
                pool{
                    id
                    token0 {decimals}
                    token1 {decimals}
                }
                baseLiquidity
                baseLower
                baseUpper
                baseFeeGrowthInside0LastX128
                baseFeeGrowthInside1LastX128
                limitLiquidity
                limitFeeGrowthInside0LastX128
                limitFeeGrowthInside1LastX128
                limitLower
                limitUpper
                conversion {
                    baseTokenIndex
                    priceTokenInBase
                    priceBaseInUSD
                }
                tvlUSD
            }
        }
        """
        hypervisor_variables = {"id": hypervisor_address.lower()}
        hypervisor_response = await self.gamma_client.query(
            hypervisor_query, hypervisor_variables
        )
        hypervisor_data = hypervisor_response["data"]["uniswapV3Hypervisor"]

        pool_query = """
        query pool(
            $poolAddress: String!,
            $baseLower: Int!
            $baseUpper: Int!
            $limitLower: Int!
            $limitUpper: Int!
        ){
            pool(id: $poolAddress){
                tick
                feeGrowthGlobal0X128
                feeGrowthGlobal1X128
            }
            baseLower: ticks(
                where: {
                poolAddress: $poolAddress
                tickIdx: $baseLower
                }
            ){
                tickIdx
                feeGrowthOutside0X128
                feeGrowthOutside1X128
            },
            baseUpper: ticks(
                where: {
                poolAddress: $poolAddress
                tickIdx: $baseUpper
                }
            ){
                tickIdx
                feeGrowthOutside0X128
                feeGrowthOutside1X128
            },
            limitLower: ticks(
                where: {
                poolAddress: $poolAddress
                tickIdx: $limitLower
                }
            ){
                tickIdx
                feeGrowthOutside0X128
                feeGrowthOutside1X128
            },
            limitUpper: ticks(
                where: {
                poolAddress: $poolAddress
                tickIdx: $limitUpper
                }
            ){
                tickIdx
                feeGrowthOutside0X128
                feeGrowthOutside1X128
            }
        }
        """
        variables = {
            "poolAddress": hypervisor_data["pool"]["id"],
            "baseLower": hypervisor_data["baseLower"],
            "baseUpper": hypervisor_data["baseUpper"],
            "limitLower": hypervisor_data["limitLower"],
            "limitUpper": hypervisor_data["limitUpper"],
        }
        pool_response = await self.uniswap_client.query(pool_query, variables)
        tick_data = pool_response["data"]

        self.fees_data = {"hypervisor_data": hypervisor_data, "tick_data": tick_data}

        return True


class HypervisorInfo(HypervisorData):
    def empty_returns(self):
        return {
            period: {
                "cumFeeReturn": 0.0,
                "feeApr": 0,
                "feeApy": 0,
                "totalPeriodSeconds": 0,
            }
            for period in DAYS_IN_PERIOD
        }

    def _calculate_returns(self, rebalance_data, uncollected_fees_data=None):
        # Calculations require more than 1 rebalance

        if rebalance_data:
            data = rebalance_data.copy()
            if uncollected_fees_data:
                data.append(uncollected_fees_data)
        else:
            data = [uncollected_fees_data]

        if (not data) or (len(data) < 2):
            return self.empty_returns()

        df_rebalances = DataFrame(data)
        df_rebalances = df_rebalances[
            [
                "timestamp",
                "grossFeesUSD",
                "protocolFeesUSD",
                "netFeesUSD",
                "totalAmountUSD",
            ]
        ].astype(np.float64)
        df_rebalances = df_rebalances[df_rebalances.totalAmountUSD > 0]

        if df_rebalances.empty:
            return self.empty_returns()

        df_rebalances.sort_values("timestamp", inplace=True)
        latest_rebalance_ts = df_rebalances.loc[df_rebalances.index[-1], "timestamp"]

        # Calculate fee return rate for each rebalance event
        shift = 1 if self.chain == "mainnet" else 0

        df_rebalances[
            "feeRate"
        ] = df_rebalances.grossFeesUSD / df_rebalances.totalAmountUSD.shift(shift)
        df_rebalances["totalRate"] = (
            df_rebalances.totalAmountUSD / df_rebalances.totalAmountUSD.shift(shift) - 1
        )

        # Time since last rebalance
        df_rebalances["periodSeconds"] = df_rebalances.timestamp.diff()
        print(df_rebalances[["timestamp", "feeRate", "grossFeesUSD", "totalAmountUSD"]])
        # Calculate returns for using last 1, 7, and 30 days data
        results = {}
        for period, days in DAYS_IN_PERIOD.items():
            timestamp_start = timestamp_ago(timedelta(days=days))
            #  If no items for timestamp larger than timestamp_start
            n_valid_rows = len(df_rebalances[df_rebalances.timestamp > timestamp_start])
            if n_valid_rows < 2:
                timestamp_start = latest_rebalance_ts - (
                    FALLBACK_DAYS * SECONDS_IN_DAYS
                )
            df_period = df_rebalances.loc[
                df_rebalances.timestamp > timestamp_start
            ].copy()

            if df_period.empty:
                # if no rebalances in the last 24 hours, calculate using the 24 hours prior to the last rebalance
                timestamp_start = df_rebalances.timestamp.max() - DAY_SECONDS
                df_period = df_rebalances.loc[
                    df_rebalances.timestamp > timestamp_start
                ].copy()

            # Time since first reblance
            df_period["totalPeriodSeconds"] = df_period.periodSeconds.cumsum()

            # Compound fee return rate for each rebalance
            df_period["cumFeeReturn"] = (1 + df_period.feeRate).cumprod() - 1
            df_period["cumTotalReturn"] = (1 + df_period.totalRate).cumprod() - 1

            # Last row is the cumulative results
            returns = df_period[["totalPeriodSeconds", "cumFeeReturn"]].tail(
                1
            )  # , 'cumTotalReturn'

            # Extrapolate linearly to annual rate
            returns["feeApr"] = returns.cumFeeReturn * (
                YEAR_SECONDS / returns.totalPeriodSeconds
            )

            # Extrapolate by compounding
            returns["feeApy"] = (
                1 + returns.cumFeeReturn * (DAY_SECONDS / returns.totalPeriodSeconds)
            ) ** 365 - 1

            results[period] = returns.to_dict("records")[0]

        if results["monthly"]["feeApy"] == np.inf:
            results["monthly"] = results["weekly"]

        return results

    async def basic_stats(self, hypervisor_address):
        data = await self._get_hypervisor_data(hypervisor_address)
        return data

    async def calculate_returns(self, hypervisor_address):
        rebalance_data = await self.get_rebalance_data(
            hypervisor_address, timedelta(days=360)
        )
        # uncollected_fees_data = await UncollectedFees(
        #     self.chain
        # ).output_for_returns_calc(hypervisor_address)
        uncollected_fees_data = None
        returns = self._calculate_returns(rebalance_data, uncollected_fees_data)

        return self.apply_returns_overrides(hypervisor_address, returns)

    async def all_returns(self, get_data=True):

        if get_data:
            await self._get_all_rebalance_data(timedelta(days=360))

        results = {}
        for hypervisor in self.all_rebalance_data:
            if hypervisor["id"] not in EXCLUDED_HYPERVISORS:
                # uncollected_fees_data = await UncollectedFees(
                #     self.chain
                # ).output_for_returns_calc(hypervisor["id"])
                uncollected_fees_data = None
                returns = self._calculate_returns(
                    hypervisor["rebalances"], uncollected_fees_data
                )
                results[hypervisor["id"]] = self.apply_returns_overrides(
                    hypervisor["id"], returns
                )

        return results

    async def all_data(self, get_data=True):

        if get_data:
            await self._get_all_data()

        basics = self.basics_data
        pools = self.pools_data

        returns = await self.all_returns(get_data=get_data)

        results = {}
        for hypervisor in basics:
            try:
                hypervisor_id = hypervisor["id"]
                hypervisor_name = f'{hypervisor["pool"]["token0"]["symbol"]}-{hypervisor["pool"]["token1"]["symbol"]}-{hypervisor["pool"]["fee"]}'
                pool_id = hypervisor["pool"]["id"]
                decimals0 = hypervisor["pool"]["token0"]["decimals"]
                decimals1 = hypervisor["pool"]["token1"]["decimals"]
                tick = int(pools[pool_id]["tick"]) if pools[pool_id]["tick"] else 0
                baseLower = int(hypervisor["baseLower"])
                baseUpper = int(hypervisor["baseUpper"])
                totalSupply = int(hypervisor["totalSupply"])
                maxTotalSupply = int(hypervisor["maxTotalSupply"])
                capacityUsed = (
                    totalSupply / maxTotalSupply if maxTotalSupply > 0 else "No cap"
                )

                results[hypervisor_id] = {
                    "createDate": timestamp_to_date(
                        int(hypervisor["created"]), "%d %b, %Y"
                    ),
                    "poolAddress": pool_id,
                    "name": hypervisor_name,
                    "decimals0": decimals0,
                    "decimals1": decimals1,
                    "depositCap0": int(hypervisor["deposit0Max"]) / 10**decimals0,
                    "depositCap1": int(hypervisor["deposit1Max"]) / 10**decimals1,
                    "grossFeesClaimed0": int(hypervisor["grossFeesClaimed0"])
                    / 10**decimals0,
                    "grossFeesClaimed1": int(hypervisor["grossFeesClaimed1"])
                    / 10**decimals1,
                    "grossFeesClaimedUSD": hypervisor["grossFeesClaimedUSD"],
                    "feesReinvested0": int(hypervisor["feesReinvested0"])
                    / 10**decimals0,
                    "feesReinvested1": int(hypervisor["feesReinvested1"])
                    / 10**decimals1,
                    "feesReinvestedUSD": hypervisor["feesReinvestedUSD"],
                    "tvl0": int(hypervisor["tvl0"]) / 10**decimals0,
                    "tvl1": int(hypervisor["tvl1"]) / 10**decimals1,
                    "tvlUSD": hypervisor["tvlUSD"],
                    "totalSupply": totalSupply,
                    "maxTotalSupply": maxTotalSupply,
                    "capacityUsed": capacityUsed,
                    "sqrtPrice": pools[pool_id]["sqrtPrice"],
                    "tick": tick,
                    "baseLower": baseLower,
                    "baseUpper": baseUpper,
                    "inRange": bool(baseLower <= tick <= baseUpper),
                    "observationIndex": pools[pool_id]["observationIndex"],
                    "poolTvlUSD": pools[pool_id]["totalValueLockedUSD"],
                    "poolFeesUSD": pools[pool_id]["feesUSD"],
                    "returns": returns.get(hypervisor_id),
                }
            except Exception as e:
                logger.warning(f"Failed on hypervisor {hypervisor['id']}")
                logger.exception(e)
                pass

        return results

    def apply_returns_overrides(self, hypervisor_address, returns):
        if hypervisor_address == "0x717a3276bd6f9e2f0ae447e0ffb45d0fa1c2dc57":
            returns["daily"] = {
            "totalPeriodSeconds": 629817,
            "cumFeeReturn": 6.317775,
            "feeApr": 0.0168880097306676,
            "feeApy": 0.01703102099
            }
        if hypervisor_address in [
            "0x3cca05926af387f1ab4cd45ce8975d31f0469927",
            "0x717a3276bd6f9e2f0ae447e0ffb45d0fa1c2dc57",
        ]:
            print("override")
            returns["weekly"] = returns["daily"]

        return returns


class UncollectedFees(HypervisorData):
    async def output(self, hypervisor_address, get_data=True):
        if get_data:
            await self._get_uncollected_fees_data(hypervisor_address)

        data = self.fees_data

        decimals_0 = int(data["hypervisor_data"]["pool"]["token0"]["decimals"])
        decimals_1 = int(data["hypervisor_data"]["pool"]["token1"]["decimals"])

        try:
            base_fees_0, base_fees_1 = self.calc_fees(
                decimals_0=decimals_0,
                decimals_1=decimals_1,
                fee_growth_global_0=int(
                    data["tick_data"]["pool"]["feeGrowthGlobal0X128"]
                ),
                fee_growth_global_1=int(
                    data["tick_data"]["pool"]["feeGrowthGlobal1X128"]
                ),
                tick_current=int(data["tick_data"]["pool"]["tick"]),
                tick_lower=int(data["hypervisor_data"]["baseLower"]),
                tick_upper=int(data["hypervisor_data"]["baseUpper"]),
                fee_growth_outside_0_lower=int(
                    data["tick_data"]["baseLower"][0]["feeGrowthOutside0X128"]
                ),
                fee_growth_outside_1_lower=int(
                    data["tick_data"]["baseLower"][0]["feeGrowthOutside1X128"]
                ),
                fee_growth_outside_0_upper=int(
                    data["tick_data"]["baseUpper"][0]["feeGrowthOutside0X128"]
                ),
                fee_growth_outside_1_upper=int(
                    data["tick_data"]["baseUpper"][0]["feeGrowthOutside1X128"]
                ),
                liquidity=int(data["hypervisor_data"]["baseLiquidity"]),
                fee_growth_inside_last_0=int(
                    data["hypervisor_data"]["baseFeeGrowthInside0LastX128"]
                ),
                fee_growth_inside_last_1=int(
                    data["hypervisor_data"]["baseFeeGrowthInside1LastX128"]
                ),
            )
        except IndexError:
            base_fees_0 = 0
            base_fees_1 = 0

        base_fees_0 = max(base_fees_0, 0)
        base_fees_1 = max(base_fees_1, 0)

        try:
            limit_fees_0, limit_fees_1 = self.calc_fees(
                decimals_0=decimals_0,
                decimals_1=decimals_1,
                fee_growth_global_0=int(
                    data["tick_data"]["pool"]["feeGrowthGlobal0X128"]
                ),
                fee_growth_global_1=int(
                    data["tick_data"]["pool"]["feeGrowthGlobal1X128"]
                ),
                tick_current=int(data["tick_data"]["pool"]["tick"]),
                tick_lower=int(data["hypervisor_data"]["limitLower"]),
                tick_upper=int(data["hypervisor_data"]["limitUpper"]),
                fee_growth_outside_0_lower=int(
                    data["tick_data"]["limitLower"][0]["feeGrowthOutside0X128"]
                ),
                fee_growth_outside_1_lower=int(
                    data["tick_data"]["limitLower"][0]["feeGrowthOutside1X128"]
                ),
                fee_growth_outside_0_upper=int(
                    data["tick_data"]["limitUpper"][0]["feeGrowthOutside0X128"]
                ),
                fee_growth_outside_1_upper=int(
                    data["tick_data"]["limitUpper"][0]["feeGrowthOutside1X128"]
                ),
                liquidity=int(data["hypervisor_data"]["limitLiquidity"]),
                fee_growth_inside_last_0=int(
                    data["hypervisor_data"]["limitFeeGrowthInside0LastX128"]
                ),
                fee_growth_inside_last_1=int(
                    data["hypervisor_data"]["limitFeeGrowthInside1LastX128"]
                ),
            )
        except IndexError:
            limit_fees_0 = 0
            limit_fees_1 = 0

        limit_fees_0 = max(limit_fees_0, 0)
        limit_fees_1 = max(limit_fees_1, 0)

        # Convert to USD
        baseTokenIndex = int(data["hypervisor_data"]["conversion"]["baseTokenIndex"])
        priceTokenInBase = float(
            data["hypervisor_data"]["conversion"]["priceTokenInBase"]
        )
        priceBaseInUSD = float(data["hypervisor_data"]["conversion"]["priceBaseInUSD"])

        if baseTokenIndex == 0:
            base_fees_0_usd = base_fees_0 * priceBaseInUSD
            base_fees_1_usd = base_fees_1 * priceTokenInBase * priceBaseInUSD
            limit_fees_0_usd = limit_fees_0 * priceBaseInUSD
            limit_fees_1_usd = limit_fees_1 * priceTokenInBase * priceBaseInUSD
        elif baseTokenIndex == 1:
            base_fees_0_usd = base_fees_0 * priceTokenInBase * priceBaseInUSD
            base_fees_1_usd = base_fees_1 * priceBaseInUSD
            limit_fees_0_usd = limit_fees_0 * priceTokenInBase * priceBaseInUSD
            limit_fees_1_usd = limit_fees_1 * priceBaseInUSD
        else:
            base_fees_0_usd = 0
            base_fees_1_usd = 0
            limit_fees_0_usd = 0
            limit_fees_1_usd = 0

        return {
            "base_fees_0": base_fees_0 / 10**decimals_0,
            "base_fees_1": base_fees_1 / 10**decimals_1,
            "limit_fees_0": limit_fees_0 / 10**decimals_0,
            "limit_fees_1": limit_fees_1 / 10**decimals_1,
            "base_fees_0_usd": base_fees_0_usd,
            "base_fees_1_usd": base_fees_1_usd,
            "limit_fees_0_usd": limit_fees_0_usd,
            "limit_fees_1_usd": limit_fees_1_usd,
            "tvl_usd": float(data["hypervisor_data"]["tvlUSD"]),
        }

    async def output_for_returns_calc(self, hypervisor_address, get_data=True):
        fees = await self.output(hypervisor_address, get_data)

        gross_fees = max(
            (
                fees["base_fees_0_usd"]
                + fees["base_fees_1_usd"]
                + fees["limit_fees_0_usd"]
                + fees["limit_fees_1_usd"]
            ),
            0,
        )

        return {
            "id": "uncollected_fees",
            "timestamp": timestamp_ago(timedelta(0)),
            "grossFeesUSD": gross_fees,
            "protocolFeesUSD": gross_fees * 0.1,
            "netFeesUSD": gross_fees * 0.9,
            "totalAmountUSD": fees["tvl_usd"],
        }

    @staticmethod
    def calc_fees(
        decimals_0,
        decimals_1,
        fee_growth_global_0,
        fee_growth_global_1,
        tick_current,
        tick_lower,
        tick_upper,
        fee_growth_outside_0_lower,
        fee_growth_outside_1_lower,
        fee_growth_outside_0_upper,
        fee_growth_outside_1_upper,
        liquidity,
        fee_growth_inside_last_0,
        fee_growth_inside_last_1,
    ):
        X128 = math.pow(2, 128)

        debug = {
            "decimals_0": decimals_0,
            "decimals_1": decimals_1,
            "fee_growth_global_0": fee_growth_global_0,
            "fee_growth_global_1": fee_growth_global_1,
            "tick_current": tick_current,
            "tick_lower": tick_lower,
            "tick_upper": tick_upper,
            "fee_growth_outside_0_lower": fee_growth_outside_0_lower,
            "fee_growth_outside_1_lower": fee_growth_outside_1_lower,
            "fee_growth_outside_0_upper": fee_growth_outside_0_upper,
            "fee_growth_outside_1_upper": fee_growth_outside_1_upper,
            "liquidity": liquidity,
            "fee_growth_inside_last_0": fee_growth_inside_last_0,
            "fee_growth_inside_last_1": fee_growth_inside_last_1,
        }

        if tick_current >= tick_lower:
            fee_growth_below_pos_0 = fee_growth_outside_0_lower
            fee_growth_below_pos_1 = fee_growth_outside_1_lower
        else:
            fee_growth_below_pos_0 = fee_growth_global_0 - fee_growth_outside_0_lower
            fee_growth_below_pos_1 = fee_growth_global_1 - fee_growth_outside_1_lower

        if tick_current >= tick_upper:
            fee_growth_above_pos_0 = fee_growth_global_0 - fee_growth_outside_0_upper
            fee_growth_above_pos_1 = fee_growth_global_1 - fee_growth_outside_1_upper
        else:
            fee_growth_above_pos_0 = fee_growth_outside_0_upper
            fee_growth_above_pos_1 = fee_growth_outside_1_upper

        fees_accum_now_0 = (
            fee_growth_global_0 - fee_growth_below_pos_0 - fee_growth_above_pos_0
        )
        fees_accum_now_1 = (
            fee_growth_global_1 - fee_growth_below_pos_1 - fee_growth_above_pos_1
        )

        uncollectedFees_0 = (
            liquidity * (fees_accum_now_0 - fee_growth_inside_last_0)
        ) / X128
        uncollectedFees_1 = (
            liquidity * (fees_accum_now_1 - fee_growth_inside_last_1)
        ) / X128

        return uncollectedFees_0, uncollectedFees_1
