ContractScreener
================
### version 0.1.0

Program that screens specified contract addresses for transactions and alerts via a Telegram message if something
of interest is found. Currently supports the following networks:
[Ethereum](https://etherscan.io), [Optimism](https://optimistic.etherscan.io/),
[Arbitrum](https://arbiscan.io/), [Polygon](https://polygonscan.com), [Gnosis](https://blockscout.com/xdai/mainnet/).

-------------------------------------------------------------------------------------------------------------------------

## Installation

This project uses **Python 3.9**

Clone the project:
```
git clone https://github.com/ivandimitrovkyulev/ContractScreener

cd ContractScreener
```

Activate virtual environment:

```
poetry shell
```

Install all third-party project dependencies:
```
poetry install
```

You will need to apply for API access and save the following variables in a **.env** file in ./ContractScreener/:
```dotenv
TOKEN=<telegram-token-for-your-bot>
CHAT_ID_ALERTS=<id-of-telegram-chat-for-alerts>
CHAT_ID_DEBUG=<id-of-telegram-chat-for-debugging>

WEB3_INFURA_ETHEREUM=<project-id-from-node>
WEB3_INFURA_OPTIMISM=<project-id-from-node>
WEB3_INFURA_ARBITRUM=<project-id-from-node>
WEB3_INFURA_POLYGON=<project-id-from-node>

OPTIMISM_API_KEY=<etherscan-optimism-api-key>
ARBITRUM_API_KEY=<etherscan-arbitrum-api-key>
POLYGON_API_KEY=<etherscan-polygon-api-key>
GNOSIS_API_KEY=<etherscan-gnosis-api-key>
```
Depending on what chains will be screened, not all API Keys will apply. 

## Running the script

To screen for new smart contract transactions:
```
var="$(cat etherscan.json)"
python3 etherscan.py -t "$var"
```

Where **etherscan.json** are variables for screening:
```json
{ 
    "settings": {
        "filter_by": ["to", "0x0000000000000000000000000000000000000000"],
        "sleep_time": 6
    },
    "contracts": {
        "uniswap_pool": {
            "url": "https://etherscan.io/address/0xa3C68a491778952Cb1257FC9909a437a0173b63a",
            "contract_address": "0xa3C68a491778952Cb1257FC9909a437a0173b63a",
            "network": "Ethereum"
        },
        "balancer_pool": {
            "url": "https://optimistic.etherscan.io/address/0xDt269D3E0d71A15a0bA976b7DBF8805bF844AA6A",
            "contract_address": "0xDt269D3E0d71A15a0bA976b7DBF8805bF844AA6A",
            "network": "Optimism"
        }
    }
}
```

<br>

To screen for new smart contract Erc20 transactions:
```
var="$(cat etherscan.json)"
python3 etherscan.py -e "$var"
```

Where **etherscan.json** are Network and screening variables of the following schema:
```json
{   
  
    "optimism_usdt": {
        "token": "USDT",
        "url": "https://optimistic.etherscan.io/address/0x9D669D3E0d61A05a0bA976b7DBF8805bF844AD3H",
        "address": "0x9D669D3E0d61A05a0bA976b7DBF8805bF844AD3H",
        "network": "Optimism",
        "decimals": 6,
        "min_amount": 30000
    },
    "arbitrum_usdc": {
        "token": "USDC",
        "url": "https://arbiscan.io/address/0xe32d2bedb3eca35e6397e0c6d62857094aa26f52",
        "address": "0xe32d2bedb3eca35e6397e0c6d62857094aa26f52",
        "network": "Arbitrum",
        "decimals": 6,
        "min_amount": 50000
    }
}
```

For help:
```
python3 etherscan.py --help
```

## Docker deployment

```
# Build docker images
docker build . -t <image_name>

# Run docker container
docker run --name="etherscan" -it "<image_name>" python3 etherscan.py -e "$(cat etherscan.json)"
```

Additionally, you can start screening whether docker container is still running:
```
docker cp etherscan:/etherscan/.env . | chmod go-rw .env
nohup python3 container_check.py etherscan &
```

<br/>
Email: <a href="mailto:ivandkyulev@gmail.com">ivandkyulev@gmail.com</a>
