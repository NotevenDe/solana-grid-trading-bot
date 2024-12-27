from solana.rpc.api import Client
from solders.keypair import Keypair 
RPC = "https://api.mainnet-beta.solana.com"

UNIT_BUDGET =  100_000
UNIT_PRICE =  1_000_000
client = Client(RPC)
PRIV_KEY = []

# Keypair = Keypair()
payer_keypair = Keypair.from_bytes(PRIV_KEY)

grid_size = 100 # 网格数量
Price_low = 0.7
Price_high = 0.8

token_address = "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr"  
sol_in = 0.01
slippage = 1 #滑点
percentage = 100
