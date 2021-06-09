import os

V3_FACTORY_ADDRESS = "0x1F98431c8aD98523631AE4a59f267346ea31F984"

V3_SUBGRAPH_ADDRESS = "https://api.thegraph.com/subgraphs/name/ianlapham/uniswap-v3-testing"


visor_subgraphs = {
    'prod': "https://api.thegraph.com/subgraphs/name/visorfinance/visor",
    'test': "https://api.thegraph.com/subgraphs/name/l0c4t0r/visor",
}

VISOR_SUBGRAPH_URL = visor_subgraphs[os.environ.get('VISOR_SUBGRAPH', 'prod')]


TOKEN_LIST_URL = "https://tokens.coingecko.com/uniswap/all.json"

DEFAULT_BBAND_INTERVALS = 20
