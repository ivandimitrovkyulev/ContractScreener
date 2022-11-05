import os
import sys
import json
import asyncio

from copy import deepcopy
from atexit import register
from datetime import datetime
from time import (
    sleep,
    perf_counter,
)
from concurrent.futures import ThreadPoolExecutor

from src.contractscreener.blockchain.interface import args
from src.contractscreener.blockchain.evm import EvmContract
from src.contractscreener.blockchain.helpers import (
    print_start_message,
    gather_funcs,
)
from src.contractscreener.common.message import telegram_send_message
from src.contractscreener.common.exceptions import exit_handler
from src.contractscreener.variables import time_format


if len(sys.argv) != 3:
    sys.exit(f"Usage: python3 {os.path.basename(__file__)} <mode> etherscan.json\n")

# Send telegram debug message if program terminates
timestamp = datetime.now().astimezone().strftime(time_format)
program_name = os.path.abspath(os.path.basename(__file__))
register(exit_handler, program_name)

# Fetch variables
info = json.loads(sys.argv[-1])
contr_addresses = [contr for contr in info['contracts'].values()]

filter_by = tuple(info['settings']['filter_by'])
sleep_time = info['settings']['sleep_time']

print(f"{timestamp} - Started screening:\n")
print_start_message(contr_addresses)

# Create a contract instance only once and then query multiple times
arguments = [[item['network'], item['contract_address']] for item in contr_addresses]

with ThreadPoolExecutor(max_workers=len(contr_addresses)) as pool:
    results = pool.map(lambda p: EvmContract(*p), arguments, timeout=20)

evm_contracts = list(results)
contract_instances = [contract for contract in evm_contracts if contract.contract]
print(f"Initialised {len(contract_instances)}/{len(contr_addresses)} contract instances. "
      f"Look at log files for more details.")


if args.transactions:
    print(f"Screening for 'Transactions' and filtering by {filter_by}:")

    txn_args = [[contr['contract_address'], 100, filter_by] for contr in contr_addresses]
    txn_funcs = [contract.get_last_txns for contract in evm_contracts]

elif args.erc20tokentxns:
    print(f"Screening for 'Erc20 Token Txns' and filtering by {filter_by}:")

    txn_args = [[contr['token_address'], 100, filter_by] for contr in contr_addresses]
    txn_funcs = [contract.get_last_erc20_txns for contract in evm_contracts]

else:
    sys.exit()

telegram_send_message(f"✅ ETHERSCAN has started.")

old_txns = asyncio.run(gather_funcs(txn_funcs, txn_args))

loop_counter = 1
while True:
    # Wait for new transactions to appear
    start = perf_counter()
    sleep(sleep_time)

    new_txns = asyncio.run(gather_funcs(txn_funcs, txn_args))

    for i, item in enumerate(contr_addresses):

        # If empty list returned - no point to compare
        if not new_txns[i]:
            continue

        # Compare new and old txns
        found_txns = EvmContract.compare_lists(new_txns[i], old_txns[i])

        # If new txns found - check them and send the interesting ones
        if found_txns:
            if args.erc20tokentxns:
                evm_contracts[i].alert_erc20_txns(txns=found_txns, min_txn_amount=item['min_amount'])
            elif args.transactions:
                evm_contracts[i].alert_checked_txns(txns=found_txns)

            # Save latest txns in old_txns only if there is a found txn
            old_txns[i] = deepcopy(new_txns[i])

    timestamp = datetime.now().astimezone().strftime(time_format)
    print(f"{timestamp} - Loop {loop_counter} executed in {(perf_counter() - start):,.2f} secs.")
    loop_counter += 1
