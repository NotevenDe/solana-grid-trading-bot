import base64
import os
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import requests
from solana.rpc.commitment import Processed
from solana.rpc.types import TokenAccountOpts, TxOpts
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.system_program import CreateAccountWithSeedParams, create_account_with_seed
from solders.transaction import VersionedTransaction
from spl.token.instructions import (InitializeAccountParams, create_associated_token_account,
                                  get_associated_token_address, initialize_account)

from utils.constants import SOL_DECIMAL, TOKEN_PROGRAM_ID, WSOL
from utils.layouts import ACCOUNT_LAYOUT
from utils.utils import (confirm_txn, fetch_pool_keys, get_token_balance,
                       get_token_reserves, make_swap_instruction, sol_for_tokens,
                       tokens_for_sol, get_pair_address_from_api)
from config import UNIT_BUDGET, UNIT_PRICE, PRIV_KEY,client, payer_keypair, token_address,grid_size,Price_low,Price_high,sol_in,slippage,percentage

@dataclass
class GridConfig:
    unit_budget: int        
    unit_price: int        
    priv_key: str         
    client: any             
    payer_keypair: any    
    token_address: str    
    grid_size: int        
    price_low: float     
    price_high: float     
    sol_amount: float     
    slippage: float       
    percentage: float     

class GridTradingBot:
    def __init__(self, config: GridConfig):
        self.config = config
        self.public_key = config.payer_keypair.pubkey()
        self.pool_keys = None
        self.token_account = None
        self.grid_levels = []
        self.last_trade_price = None
        self.last_trade_action = None
        self.setup_grid()

    def setup_grid(self):
        price_range = self.config.price_high - self.config.price_low
        grid_step = price_range / self.config.grid_size
        self.grid_levels = [
            self.config.price_low + (i * grid_step) 
            for i in range(self.config.grid_size + 1)
        ]
        print(f"网格价格区间：${self.config.price_low} - ${self.config.price_high}")
        print(f"网格间距：${grid_step:.4f}")


    def get_sol_price(self) -> float:
        response = requests.get(
            'https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd'
        )
        return response.json()['solana']['usd']

    def initialize_pool(self) -> None:
        print("正在初始化交易池...")
        pair_address = get_pair_address_from_api(self.config.token_address)
        self.pool_keys = fetch_pool_keys(pair_address)
        self.mint = (self.pool_keys.base_mint 
                    if self.pool_keys.base_mint != WSOL 
                    else self.pool_keys.quote_mint)
        
        print("检查代币账户...")
        token_account_check = self.config.client.get_token_accounts_by_owner(
            self.public_key,
            TokenAccountOpts(self.mint),
            Processed
        )
        
        
        if token_account_check.value:
            self.token_account = token_account_check.value[0].pubkey
            print("已找到现有代币账户")
            return None
        else:
            self.token_account = get_associated_token_address(self.public_key, self.mint)
            print("创建新代币账户")
            return create_associated_token_account(
                self.public_key,
                self.public_key,
                self.mint
            )

    def create_wsol_account(self, wsol_amount: int) -> Tuple[Pubkey, list]:
        print("创建WSOL账户...")
        seed = base64.urlsafe_b64encode(os.urandom(24)).decode('utf-8')
        wsol_token_account = Pubkey.create_with_seed(
            self.public_key, seed, TOKEN_PROGRAM_ID
        )
        
        balance_needed = self.config.client.get_minimum_balance_for_rent_exemption(
            ACCOUNT_LAYOUT.sizeof()
        ).value
        
        create_instr = create_account_with_seed(
            CreateAccountWithSeedParams(
                from_pubkey=self.public_key,
                to_pubkey=wsol_token_account,
                base=self.public_key,
                seed=seed,
                lamports=int(balance_needed + wsol_amount),
                space=ACCOUNT_LAYOUT.sizeof(),
                owner=TOKEN_PROGRAM_ID
            )
        )
        
        init_instr = initialize_account(
            InitializeAccountParams(
                program_id=TOKEN_PROGRAM_ID,
                account=wsol_token_account,
                mint=WSOL,
                owner=self.public_key
            )
        )
        
        return wsol_token_account, [create_instr, init_instr] 
    def execute_trade(self, action: str, amount_in: int, 
                     minimum_out: int) -> Optional[str]:
        print(f"执行{action}交易...")
        current_price = self.get_token_price()
        if self.last_trade_price is not None:
            if action == "sell" and current_price <= self.last_trade_price:
                print(f"跳过卖出 - 当前价格(${current_price:.4f}) 未高于上次交易价格(${self.last_trade_price:.4f})")
                return None
            elif action == "buy" and self.last_trade_action == "buy":
                print(f"跳过买入 - 上次操作已是买入")
                return None
        print(f"输入数量: {amount_in}, 最小输出: {minimum_out}")
        
        wsol_amount = int(self.config.sol_amount * SOL_DECIMAL)
        wsol_account, wsol_instructions = self.create_wsol_account(wsol_amount)
        
        if action == "buy":
            swap_instr = make_swap_instruction(
                amount_in,
                minimum_out,
                wsol_account,
                self.token_account,
                self.pool_keys,
                self.config.payer_keypair
            )
        else:
            swap_instr = make_swap_instruction(
                amount_in,
                minimum_out,
                self.token_account,
                wsol_account,
                self.pool_keys,
                self.config.payer_keypair
            )

        instructions = [
            set_compute_unit_limit(self.config.unit_budget),
            set_compute_unit_price(self.config.unit_price),
            *wsol_instructions,
            swap_instr
        ]

        compiled_message = MessageV0.try_compile(
            self.public_key,
            instructions,
            [],
            self.config.client.get_latest_blockhash().value.blockhash,
        )
        
        txn = VersionedTransaction(
            compiled_message, 
            [self.config.payer_keypair]
        )
        
        try:
            print("发送交易...")
            txn_sig = self.config.client.send_transaction(
                txn=txn,
                opts=TxOpts(skip_preflight=True)
            ).value
            result = confirm_txn(txn_sig)
            print(f"交易结果: {result}")
            if result:  # 更新价格
              self.last_trade_price = current_price
              self.last_trade_action = action
            return result
        except Exception as e:
            print(f"交易失败: {e}")
            return None

    def calculate_amounts(self, action: str) -> Tuple[int, int]:
        based_token, quote_token, base_reserve, quote_reserve, token_decimal = (
            get_token_reserves(self.pool_keys)
        )
        
        if action == "buy":
            amount_in = int(self.config.sol_amount * SOL_DECIMAL)
            amount_out = sol_for_tokens(
                self.config.sol_amount, 
                base_reserve, 
                quote_reserve
            )
            decimal_factor = 10**token_decimal
        else:
            token_balance = get_token_balance(str(self.mint))
            amount_in = int(token_balance * (self.config.percentage / 100))
            amount_out = tokens_for_sol(amount_in, base_reserve, quote_reserve)
            decimal_factor = SOL_DECIMAL

        slippage_adjustment = 1 - (self.config.slippage / 100)
        minimum_out = int(amount_out * slippage_adjustment * decimal_factor)
        
        return amount_in, minimum_out

    def get_token_price(self) -> float:
        _, _, base_reserve, quote_reserve, _ = get_token_reserves(self.pool_keys)
        sol_price = self.get_sol_price()
        return (quote_reserve * sol_price) / base_reserve

    def run(self):
        print("启动网格交易机器人...")
        token_account_instr = self.initialize_pool()
        based_token, quote_token, base_reserve, quote_reserve, token_decimal = (
            get_token_reserves(self.pool_keys)
        )
        print(f"based token: {based_token} | Quote token: {quote_token}")
        print(f"池子token容量: {base_reserve} | SOL 容量: {quote_reserve} | Token Decimal: {token_decimal}")    
        if token_account_instr:
            print("初始化代币账户...")
            self.execute_trade("buy", 0, 0)  # 初始化交易

        print(f"网格价格等级: {[f'${price:.4f}' for price in self.grid_levels]}")
        
        while True:
            try:
                current_price = self.get_token_price()
                print(f"\n当前代币价格: ${current_price:.4f}")

                if current_price < self.config.price_low:
                    print("价格低于网格下限 - 执行卖出")
                    amount_in, minimum_out = self.calculate_amounts("sell")
                    self.execute_trade("sell", amount_in, minimum_out)
                
                elif current_price > self.config.price_high:
                    print("价格高于网格上限 - 持仓观察")
                    
                else:
                    closest_level = min(
                        self.grid_levels, 
                        key=lambda x: abs(x - current_price)
                    )
                    print(f"最近网格价格: ${closest_level:.4f}")
                    
                    if current_price < closest_level:
                        print("执行网格买入")
                        amount_in, minimum_out = self.calculate_amounts("buy")
                        self.execute_trade("buy", amount_in, minimum_out)
                    else:
                        print("执行网格卖出")
                        amount_in, minimum_out = self.calculate_amounts("sell")
                        self.execute_trade("sell", amount_in, minimum_out)

                time.sleep(60)  
                
            except Exception as e:
                print(f"运行出错: {e}")
                time.sleep(60)  

config = GridConfig(
    unit_budget=UNIT_BUDGET,
    unit_price=UNIT_PRICE,
    priv_key=PRIV_KEY,
    client=client,
    payer_keypair=payer_keypair,
    token_address=token_address,
    grid_size=grid_size,
    price_low=Price_low,
    price_high=Price_high,
    sol_amount=sol_in,
    slippage=slippage,
    percentage=percentage
)


bot = GridTradingBot(config)
bot.run()
