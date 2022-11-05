import os
import json

from requests.exceptions import ConnectionError
from aiohttp import ClientSession
from json.decoder import JSONDecodeError

from datetime import (
    datetime,
    timezone,
)
from typing import (
    List,
    Dict,
)

from web3 import Web3
from web3.contract import Contract

from src.contractscreener.common.message import telegram_send_message
from src.contractscreener.common.logger import (
    log_txns,
    log_error,
)
from src.contractscreener.variables import (
    time_format,
    etherscans,
    http_session,
    infura_endpoints,
)


class EvmContract:

    def __init__(self, name: str, contract_address: str, web3_endpoint: str = ""):
        """
        EVM contract and transaction screener class.

        :param name: Network name
        :param contract_address: Contract address on given network
        :param web3_endpoint: Node provider network url endpoint
        """

        if name.lower() not in etherscans:
            raise ValueError(f"No such network. Choose from: {etherscans}")

        self.name = name.lower()
        self.contract_address = contract_address.lower()
        self.api = etherscans[self.name][0]
        self.web_page = etherscans[self.name][1]
        self.color = etherscans[self.name][2]

        self.node_api_key = os.getenv(f"{self.name.upper()}_API_KEY")

        self.abi_endpoint = f"{self.api}/api?module=contract&action=getabi"

        self.txn_api = f"{self.api}/api?module=account&action=txlist"

        self.erc20_api = f"{self.api}/api?module=account&action=tokentx"

        # Create contract instance
        try:
            abi = self.get_contract_abi(self.contract_address, self.name, self.abi_endpoint)
            self.contract = self.create_contract(self.name, self.contract_address, abi, web3_endpoint)
        except Exception as e:
            self.contract = None
            message = f"Contract instance not created for {self.name}, {self.contract_address}. {e}"
            log_error.warning(message)

    @staticmethod
    def run_contract_function(contract_instance: Contract, function_name: str, args_list: list):
        """
        Runs an EVM contract function by its name.

        :param contract_instance: EVM Contract
        :param function_name: Name of function to get executed
        :param args_list: List of arguments to pass to function
        :return:
        """

        function_name = str(function_name)

        contract_func = contract_instance.functions[function_name]
        result = contract_func(*args_list).call()

        return result

    @staticmethod
    def get_contract_abi(address: str, network: str, abi_endpoint: str, timeout: float = 3) -> str or None:
        """
        Queries contract's ABI using an API.

        :param address: Contract's address
        :param network: Network name, eg. Optimism
        :param abi_endpoint: Node provider api endpoint
        :param timeout: Max number of secs to wait for request
        :return: Contract's ABI
        """
        node_api_key = os.getenv(f"{network.upper()}_API_KEY")

        # Contract's ABI
        payload = {'address': address, 'apikey': node_api_key}

        try:
            url = http_session.get(abi_endpoint, params=payload, timeout=timeout)
        except ConnectionError:
            log_error.warning(f"'ConnectionError': Unable to fetch data for {abi_endpoint}")
            return None

        # Convert Contract's ABI text to JSON file
        abi = json.loads(url.text)

        return abi['result']

    @staticmethod
    def create_contract(network: str, address: str, abi: str, web3_endpoint: str = "") -> Contract:
        """
        Creates a contract instance.
        Once instantiated, you can read data and execute transactions.

        :param network: Name of Blockchain, eg. Ethereum or Optimism
        :param address: Contract's address
        :param abi: Contract's ABI
        :param web3_endpoint: Node provider network url endpoint
        :return: web3 Contract instance
        """
        if web3_endpoint == "":
            web3_endpoint = infura_endpoints[network.lower()]

        w3 = Web3(Web3.HTTPProvider(web3_endpoint))

        # Convert transaction address to check-sum address
        checksum_address = Web3.toChecksumAddress(address)

        # Create contract instance
        contract = w3.eth.contract(address=checksum_address, abi=abi)

        return contract

    @staticmethod
    def run_contract(contract: Contract, txn_input: str) -> dict:
        """
        Runs an EVM contract with a given transaction input.

        :param contract: web3 Contract instance
        :param txn_input: Transaction input field
        :return: Dictionary of transaction output
        """

        # Get transaction output from contract instance
        _, func_params = contract.decode_function_input(txn_input)

        return func_params

    @staticmethod
    def compare_lists(new_list: List[Dict[str, str]], old_list: List[Dict[str, str]],
                      keyword: str = 'hash') -> list:
        """
        Compares two lists of dictionaries.

        :param new_list: New list
        :param old_list: Old list
        :param keyword: Keyword to compare with
        :return: List of dictionaries that are in new list but not in old list
        """

        try:
            hashes = [txn[keyword] for txn in old_list]

            list_diff = [txn for txn in new_list if txn[keyword] not in hashes]

            return list_diff

        except TypeError:
            return []

    async def get_last_txns(self, contract_address: str, txn_count: int = 1,
                            filter_by: tuple = (), timeout: float = 3) -> List:
        """
        Gets the last transactions from a specified contract address.

        :param contract_address: Contract address on Blockchain
        :param txn_count: Number of transactions to return
        :param filter_by: Filter transactions by field and value, eg. ('to', '0x000...000')
        :param timeout: Max number of secs to wait for request
        :return: A list of transaction dictionaries
        """
        if int(txn_count) < 1:
            txn_count = 1

        if contract_address == "":
            contract_address = self.contract_address

        payload = {"address": contract_address, "startblock": "0", "endblock": "99999999", "sort": "desc",
                   "apikey": self.node_api_key}

        async with ClientSession(timeout=timeout) as async_session:
            try:
                async with async_session.get(self.txn_api, ssl=False, params=payload, timeout=timeout) as response:

                    try:
                        txn_dict = await response.json()
                    except JSONDecodeError:
                        log_error.warning(f"'JSONError' - {self.name} - {response.status} - {response.url}")
                        return []

            except Exception as e:
                log_error.warning(f"'ConnectionError': Unable to fetch transaction data for {self.name} - {e}")
                return []

        if txn_dict['status'] != "1":
            log_error.warning(f"'ResponseError' {response.status} - {txn_dict} - {response.url}")
            return []

        # Get a list with specified number of txns
        try:
            last_txns = txn_dict['result'][:txn_count]
        except TypeError:
            log_error.warning(f"'ResponseError' {response.status} - {txn_dict} - {response.url}")
            return []

        if len(filter_by) == 2:
            field = filter_by[0]  # Eg. 'to' or 'from'
            value = filter_by[1]  # Eg. '0x000...0000'
            try:
                temp = {t_dict['hash']: t_dict for t_dict in last_txns
                        if type(t_dict) is dict and t_dict[field] == value}

                last_txns_cleaned = [txn for txn in temp.values()]
                return last_txns_cleaned

            except KeyError:
                raise KeyError(f"Error in f'get_last_txns': Can not filter by {filter_by} for {self.name}")

        else:
            return last_txns

    async def get_last_erc20_txns(self, token_address: str, txn_count: int = 1, filter_by: tuple = (),
                                  bridge_address: str = "", timeout: float = 3) -> List:
        """
        Gets the latest Token transactions from a specific smart contract address.

        :param token_address: Address of Token contract of interest
        :param txn_count: Number of transactions to return
        :param filter_by: Filter transactions by field and value, eg. ('to', '0x000...000')
        :param bridge_address: Address of the smart contract interacting with Token
        :param timeout: Max number of secs to wait for request
        :return: A list of transaction dictionaries
        """
        if int(txn_count) < 1:
            txn_count = 1

        token_address = token_address.lower()

        if bridge_address == "":
            bridge_address = self.contract_address

        payload = {"contractaddress": token_address, "address": bridge_address, "page": "1",
                   "offset": "100", "sort": "desc", "apikey": self.node_api_key}

        async with ClientSession(timeout=timeout) as async_session:
            try:
                async with async_session.get(self.erc20_api, ssl=False, params=payload, timeout=timeout) as response:

                    try:
                        txn_dict = await response.json()
                    except JSONDecodeError:
                        log_error.warning(f"'JSONError' - {self.name} - {response.status} - {response.url}")
                        return []

            except Exception as e:
                log_error.warning(f"'ConnectionError': Unable to fetch transaction data for {self.name} - {e}")
                return []

        if txn_dict['status'] != "1":
            log_error.warning(f"'ResponseError' {response.status} - {txn_dict} - {response.url}")
            return []

        # Get a list with specified number of txns
        try:
            last_txns = txn_dict['result'][:txn_count]
        except TypeError:
            log_error.warning(f"'ResponseError' {response.status} - {txn_dict} - {response.url}")
            return []

        if len(filter_by) == 2:
            field = filter_by[0]  # Eg. 'to' or 'from'
            value = filter_by[1]  # Eg. '0x000...0000'
            try:
                temp = {t_dict['hash']: t_dict for t_dict in last_txns
                        if type(t_dict) is dict and t_dict[field] == value}

                last_txns_cleaned = [txn for txn in temp.values()]
                return last_txns_cleaned

            except KeyError:
                raise KeyError(f"Error in f'get_last_erc20_txns': Can not filter by {filter_by} for {self.name}")

        else:
            return last_txns

    def alert_checked_txns(self, txns: list) -> None:
        """
        Alerts each txn from the txn list.

        :param txns: List of transactions
        :return: None
        """
        for txn in txns:
            txn_hash = txn['hash']
            value = float(txn['value'])
            from_addr = txn['from']
            to_addr = txn['to']
            time_at_secs = int(txn['timeStamp'])
            try:
                function_name: str = txn['functionName']
                function_name = function_name.split("(")[0]
            except (KeyError, TypeError):
                function_name = 'n/a'

            txn_hash_format = f"{txn_hash[0:6]}...{txn_hash[-4:]}"  # eg. 0xc43c...37ea
            from_addr_format = f"{from_addr[0:6]}...{from_addr[-4:]}"  # eg. 0xc43c...37ea
            to_addr_format = f"{to_addr[0:6]}...{to_addr[-4:]}"  # eg. 0xc43c...37ea

            txn_stamp = datetime.fromtimestamp(time_at_secs, timezone.utc).strftime(time_format)

            try:
                txn_link = f"{self.web_page}/tx/{txn_hash}"
            except KeyError:
                txn_link = f"https://www.google.com/search?&rls=en&q={self.name}+{txn_hash}&ie=UTF-8&oe=UTF-8"

            # Construct messages
            time_stamp = datetime.now().astimezone().strftime(time_format)
            message = f"{time_stamp}\n" \
                      f"<a href='{txn_link}'>{txn_hash_format} on {self.name.title()}</a>\n" \
                      f"From {from_addr_format} -> To {to_addr_format}\n" \
                      f"Stamp:  {txn_stamp}\n" \
                      f"Type: {function_name}\n" \
                      f"Value: {value:,.3f}"

            terminal_msg = f"{txn_hash}, {self.name}"

            # Log all transactions
            log_txns.info(terminal_msg)
            telegram_send_message(message)

    def alert_erc20_txns(self, txns: list, min_txn_amount: float) -> None:
        """
        Checks transaction list and alerts if new transaction is important.

        :param txns: List of transactions
        :param min_txn_amount: Minimum transfer amount to alert for
        :return: None
        """
        for txn in txns:

            txn_amount = float(int(txn['value']) / 10 ** int(txn['tokenDecimal']))
            # round txn amount number
            rounding = int(txn['tokenDecimal']) // 6
            txn_amount = round(txn_amount, rounding)
            token_name = txn['tokenSymbol']

            # Construct messages
            time_stamp = datetime.now().astimezone().strftime(time_format)
            message = f"{time_stamp} - hop_etherscan_async\n" \
                      f"-> {txn_amount:,} {token_name} swapped on " \
                      f"<a href='{self.web_page}/tx/{txn['hash']}'>{self.name.upper()} {self.color}</a>"

            terminal_msg = f"{txn['hash']}, {txn_amount:,} {token_name} swapped on {self.name.upper()}"

            # Log all transactions
            log_txns.info(terminal_msg)

            if txn_amount >= min_txn_amount:
                # Send formatted Telegram message
                telegram_send_message(message)
