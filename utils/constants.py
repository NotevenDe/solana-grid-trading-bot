from solders.pubkey import Pubkey 

WSOL = Pubkey.from_string("So11111111111111111111111111111111111111112")

# mainnet 675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8
# devnet HWy1jotHpo6UqeQxx49dpYYdQB8wj9Qk9MdxwjLvDHB8
RAY_V4 = Pubkey.from_string("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")
# raydium pool
RAY_AUTHORITY_V4 = Pubkey.from_string("5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1")
# https://api.raydium.io/v2/sdk/liquidity/mainnet.json
OPEN_BOOK_PROGRAM = Pubkey.from_string("srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX")

TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

SOL_DECIMAL = 1e9