import sys
import os
import datetime as dt
import logging
import asyncio


logging.basicConfig(
    format="[%(asctime)s:%(levelname)s:%(name)s]:%(message)s",
    datefmt="%Y/%m/%d %I:%M:%S",
    level=logging.INFO,
)

# append parent directory pth
CURRENT_FOLDER = os.path.dirname(os.path.realpath(__file__))
PARENT_FOLDER = os.path.dirname(CURRENT_FOLDER)
sys.path.append(PARENT_FOLDER)

from v3data.constants import PROTOCOL_UNISWAP_V3, PROTOCOL_QUICKSWAP
from v3data.config import MONGO_DB_URL, GAMMA_SUBGRAPH_URLS

from database.collection_returns import db_returns_manager
from database.collection_static import db_static_manager
from v3data.common import hypervisor

from v3data.routers import mainnet, optimism, arbitrum, celo, polygon


logger = logging.getLogger(__name__)


async def test_impermanent_divergence(
    days, protocol: str = PROTOCOL_UNISWAP_V3, chain: str = "mainnet"
):

    data = await hypervisor.impermanent_divergence(
        protocol=protocol, chain=chain, days=days
    )

    # log weird data
    logger.info("[{}-{}] weird data:".format(chain, protocol))
    for hypervisor_id, data in data.items():
        for key in [
            "vs_hodl_usd",
            "vs_hodl_deposited",
            "vs_hodl_token0",
            "vs_hodl_token1",
        ]:
            if data[key] > 6:
                logger.warning("data: {} \r".format(data))


async def test_impermanent_divergence_all():
    days = [1, 7, 30]
    protocols = [PROTOCOL_UNISWAP_V3, PROTOCOL_QUICKSWAP]
    chains = ["mainnet", "polygon", "optimism", "arbitrum", "celo"]

    for chain in chains:
        for protocol in protocols:
            if protocol == PROTOCOL_QUICKSWAP and chain != "polygon":
                continue
            # elif protocol == PROTOCOL_UNISWAP_V3 and chain == "polygon":
            #     continue

            for day in days:
                await test_impermanent_divergence(
                    days=day, protocol=protocol, chain=chain
                )


async def test_all_endpoints():

    _startime = dt.datetime.utcnow()
    await mainnet.impermanent_divergence_daily()
    print(
        " took {} to complete impermanent_divergence_daily".format(
            get_timepassed_string(_startime)
        )
    )

    _startime = dt.datetime.utcnow()
    await mainnet.impermanent_divergence_weekly()
    print(
        " took {} to complete impermanent_divergence_weekly".format(
            get_timepassed_string(_startime)
        )
    )

    _startime = dt.datetime.utcnow()
    await mainnet.impermanent_divergence_monthly()
    print(
        " took {} to complete impermanent_divergence_monthly".format(
            get_timepassed_string(_startime)
        )
    )

    _startime = dt.datetime.utcnow()
    await mainnet.hypervisors_average_return()
    print(
        " took {} to complete hypervisors_average_return".format(
            get_timepassed_string(_startime)
        )
    )

    # await mainnet.hypervisor_average_apy()


def get_timepassed_string(start_time: dt.datetime) -> str:
    _timelapse = dt.datetime.utcnow() - start_time
    _passed = _timelapse.total_seconds()
    if _passed < 60:
        _timelapse_unit = "seconds"
    elif _passed < 60 * 60:
        _timelapse_unit = "minutes"
        _passed /= 60
    elif _passed < 60 * 60 * 24:
        _timelapse_unit = "hours"
        _passed /= 60 * 60
    return "{:,.2f} {}".format(_passed, _timelapse_unit)


# TESTING
if __name__ == "__main__":
    # start time log
    _startime = dt.datetime.utcnow()

    data = asyncio.run(test_impermanent_divergence_all())

    # end time log
    print(" took {} to complete the script".format(get_timepassed_string(_startime)))