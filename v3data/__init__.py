import requests

from v3data.config import (
    VISOR_SUBGRAPH_URL,
    PRICING_SUBGRAPH_URL,
    UNI_V2_SUBGRAPH_URL,
    UNI_V3_SUBGRAPH_URL,
    ETH_BLOCKS_SUBGRAPH_URL
)


class SubgraphClient:
    def __init__(self, url):
        self._url = url

    def query(self, query: str, variables=None) -> dict:
        """Make graphql query to subgraph"""
        if variables:
            params = {'query': query, 'variables': variables}
        else:
            params = {'query': query}
        response = requests.post(self._url, json=params)
        return response.json()

    def paginate_query(self, query, paginate_variable, variables={}):

        # if not variables:
        #     variables = {}

        if f"{paginate_variable}_gt" not in query:
            raise ValueError("Paginate variable missing in query")

        variables['orderBy'] = paginate_variable
        variables['orderDirection'] = "asc"

        all_data = []
        has_data = True
        params = {'query': query, 'variables': variables}
        while has_data:
            response = requests.post(self._url, json=params)
            data = next(iter(response.json()['data'].values()))
            has_data = bool(data)
            if has_data:
                all_data += data
                params['variables']['paginate'] = data[-1][paginate_variable]

        return all_data


class VisorClient(SubgraphClient):
    def __init__(self):
        super().__init__(VISOR_SUBGRAPH_URL)


class PricingClient(SubgraphClient):
    def __init__(self):
        super().__init__(PRICING_SUBGRAPH_URL)

    def hypervisors_tvl(self):
        query_tvl = """
        {
            hypervisors(first:1000) {
                id
                pool{
                    id
                    token0{
                        decimals
                    }
                    token1{
                        decimals
                    }
                }
                tvl0
                tvl1
                tvlUSD
                totalSupply
            }
        }
        """
        tvls = self.query(query_tvl)['data']['hypervisors']

        return {
            hypervisor['id']: {
                "tvl0": hypervisor['tvl0'],
                "tvl1": hypervisor['tvl1'],
                "tvlUSD": hypervisor['tvlUSD'],
                "tvl0Decimal": int(hypervisor['tvl0']) / 10 ** int(hypervisor['pool']['token0']['decimals']),
                "tvl1Decimal": int(hypervisor['tvl1']) / 10 ** int(hypervisor['pool']['token1']['decimals']),
                "totalSupply": int(hypervisor['totalSupply'])
            } for hypervisor in tvls
        }


class UniswapV2Client(SubgraphClient):
    def __init__(self):
        super().__init__(UNI_V2_SUBGRAPH_URL)


class UniswapV3Client(SubgraphClient):
    def __init__(self):
        super().__init__(UNI_V3_SUBGRAPH_URL)


class EthBlocksClient(SubgraphClient):
    def __init__(self):
        super().__init__(ETH_BLOCKS_SUBGRAPH_URL)

    def block_from_timestamp(self, timestamp):
        """Get closest from timestamp"""
        ten_minutes_in_seconds = 600
        query = """
        query blockQuery($startTime: Int!, $endTime:Int!){
          blocks(first: 1, orderBy: timestamp, orderDirection: asc,
                 where: {timestamp_gt: $startTime, timestamp_lt: $endTime}) {
            id
            number
            timestamp
          }
        }
        """

        variables = {
            "startTime": timestamp,
            "endTime": timestamp + ten_minutes_in_seconds
        }

        return int(self.query(query, variables)['data']['blocks'][0]['number'])
