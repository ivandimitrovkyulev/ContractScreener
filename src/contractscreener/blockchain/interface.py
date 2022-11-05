from argparse import ArgumentParser

from src.contractscreener import __version__


# Create CLI interface
parser = ArgumentParser(
    usage="python3 %(prog)s <command> <input file>\n",
    description="Program that screens a block explorer for contract transactions. "
                "and alerts via a Telegram message."
                "Visit https://github.com/ivandimitrovkyulev/ContractScreener for more info.",
    epilog=f"Version - {__version__}",
)

parser.add_argument(
    "-t", "--transactions", action="store", type=str, nargs=1, metavar="\b", dest="transactions",
    help=f"Screens for a new contract transaction and alerts via a Telegram message if it satisfies filter criteria."
)

parser.add_argument(
    "-e", "--erc20tokentxns", action="store", type=str, nargs=1, metavar="\b", dest="erc20tokentxns",
    help=f"Screens for a new  Erc20 Token contract transaction and alerts via a Telegram message if it satisfies"
         f" filter criteria."
)

parser.add_argument(
    "-v", "--version", action="version", version=__version__,
    help="Prints the program's current version."
)

# Parse arguments
args = parser.parse_args()
