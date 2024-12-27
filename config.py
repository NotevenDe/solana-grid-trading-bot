from solana.rpc.api import Client
from solders.keypair import Keypair 
RPC = "https://api.mainnet-beta.solana.com"

UNIT_BUDGET =  100_000
UNIT_PRICE =  1_000_000
client = Client(RPC)
PRIV_KEY = [212,172,159,1,41,82,62,125,31,246,173,224,69,205,15,69,50,61,163,254,238,210,222,41,107,120,236,32,101,182,163,89,103,110,25,128,233,108,117,22,74,22,146,253,241,30,217,93,24,226,17,78,54,250,9,12,80,122,234,104,37,171,202,63]

# Keypair = Keypair()
payer_keypair = Keypair.from_bytes(PRIV_KEY)

grid_size = 100 # 网格数量
Price_low = 0.7
Price_high = 0.8

token_address = "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr"  
sol_in = 0.01
slippage = 1 #滑点
percentage = 100