from flask import Flask, request, Response
from flask_cors import CORS

from v3data.data import UniV3Data
from v3data.pools import pools_from_symbol, Pool
from v3data.bollingerbands import BollingerBand
from v3data.hypervisor import Hypervisor
from v3data.visr import Visr
from v3data.factory import Factory

app = Flask(__name__)
CORS(app)


@app.route('/')
def main():
    return "Visor Data"


@app.route('/bollingerBandsChartData/<poolAddress>')
def bollingerbands_chart(poolAddress):
    periodHours = int(request.args.get("periodHours", 24))

    bband = BollingerBand(poolAddress, periodHours)

    return {'data': bband.chart_data()}


@app.route('/bollingerBandsLatest/<poolAddress>')
def bollingerbands_latest(poolAddress):
    periodHours = int(request.args.get("periodHours", 24))

    bband = BollingerBand(poolAddress, periodHours)

    return bband.latest_bands()


@app.route('/pools/<token>')
def uniswap_pools(token):
    return {"pools": pools_from_symbol(token)}


@app.route('/hypervisor/<hypervisorAddress>/apy')
def hypervisor_apy(hypervisorAddress):
    hypervisor = Hypervisor()
    apy = hypervisor.calculate_apy(hypervisorAddress)

    if apy:
        return apy
    else:
        return Response("Invalid hypervisor address", status=422)


# @app.route('/dashboard')
# def dashboard():
#     period = request.args.get("period", "daily").lowercase()

#     visr = Visr()
#     visr_data = visr.token_data()
#     period_estimates = visr.period_estimates()

#     pool = Pool()
#     factory = Factory()
#     v3data = UniV3Data()
#     visr_price_usd = v3data.get_visr_price_usd()

#     dashboard_stats = {
#         "stakedUsdAmount": visr_data['staked'] * visr_price_usd,
#         "stakedAmount": visr_data['staked'],
#         "feeStatsFeeAccural": "$9.5k",
#         "feeStatsAmountVisr": "72.k",
#         "feeStatsStakingApy": period_estimates[period]['apy'],
#         "feeStatsStakingDailyYield": period_estimates[period]['yield'],
#         "feeCumulativeFeeUsd": "$129k",
#         "feeCumulativeFeeUsdAnnual": "$3M",
#         "feeCumulativeFeeDistributed": visr_data['distributed'],
#         "feeCumulativeFeeDistributedAnnual": period_estimates[period]['visrDistributedAnnual'],
#         "uniswapPairTotalValueLocked": factory.tvl(),
#         "uniswapPairAmountPairs": pool.count(),
#         "uniswapFeesGenerated": "$129k",
#         "uniswapFeesBasedApr": 3.29,
#         "visrPrice": visr_price_usd,  # End point for price
#         "id": 2 # What is this?
#     }

# @app.route('/dashboard/visrDistributions')
# def visr_distributions():
#     days = int(request.args.get("days", 5))
#     visr = Visr()
#     return visr.recent_distributions(days)
