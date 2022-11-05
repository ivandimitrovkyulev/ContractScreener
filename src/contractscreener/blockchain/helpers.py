import asyncio
from typing import (
    List,
    Callable,
)
from tabulate import tabulate


def print_start_message(arguments: List[dict]) -> None:
    """Prints script start message of all network configurations.

    :param arguments: List of argument lists. Output of func paser_args
    """

    table = []
    for arg in arguments:
        network = arg['network']
        token = arg['token']
        min_amount = arg['min_amount']
        bridge_address = arg['contract_address'].lower()
        token_address = arg['token_address'].lower()

        min_amount = f"{min_amount:,} {token}"
        bridge_address = bridge_address[0:6] + "..." + bridge_address[-6:]
        token_address = token_address[0:6] + "..." + token_address[-6:]

        line = [network, token, min_amount, bridge_address, token_address]
        table.append(line)

    columns = ["Network", "Token", "Min amount", "Contract address", "Token address"]

    print(tabulate(table, headers=columns, showindex=True,
                   tablefmt="fancy_grid", numalign="left", stralign="left", colalign="left"))


async def gather_funcs(functions: List[Callable], func_args: List[list]) -> tuple:
    """
    Gathers all asyncio http requests to be scheduled.

    :param functions: List of function pointers to execute
    :param func_args: List of function arguments
    :return: List of all 1inch swaps
    """
    function_list = [function(*arg) for function, arg in zip(functions, func_args)]

    func_results = await asyncio.gather(*function_list)

    return func_results
