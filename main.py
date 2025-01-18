import os
import sys
import json
import anyio
import httpx
import random
import ssl
import asyncio
import argparse
import aiofiles
import cfcrawler
import aiofiles.os
import ua_generator
import python_socks
import aiofiles.ospath
from base64 import b64decode
from datetime import datetime
from urllib.parse import parse_qs
from fake_useragent import UserAgent
from tinydb import TinyDB, Query
from colorama import init, Fore, Style
from httpx_socks import AsyncProxyTransport

red = Fore.LIGHTRED_EX
blue = Fore.LIGHTBLUE_EX
green = Fore.LIGHTGREEN_EX
yellow = Fore.LIGHTYELLOW_EX
black = Fore.LIGHTBLACK_EX
white = Fore.LIGHTWHITE_EX
reset = Style.RESET_ALL
magenta = Fore.LIGHTMAGENTA_EX
log_file = "http.log"
proxy_file = "proxies.txt"
data_file = "data.txt"
config_file = "config.json"

ssl._create_default_https_context = ssl._create_unverified_context
os.environ['CURL_CA_BUNDLE'] = ""

# 如果还有问题，可以尝试添加这个
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context



class Config:
    def __init__(self, auto_checkin, auto_collect, auto_task, auto_upgrade ):
        self.auto_checkin = auto_checkin
        self.auto_collect = auto_collect
        self.auto_task = auto_task
        self.auto_upgrade = auto_upgrade

class PIN_AI:
    def __init__(self, id, query, proxies, config: Config):
        self.db = TinyDB("db.json")
        self.p = id
        self.query = query
        self.proxies = proxies
        self.cfg = config
        self.valid = True
        parser = {key: value[0] for key, value in parse_qs(query).items()}
        user = parser.get("user")

        if user is None:
            self.valid = False
            self.log(f"this account data has the wrong formart.")
            return None
        self.user = json.loads(user)
        if len(self.proxies) > 0:
            proxy = self.get_random_proxy(id, False)
            transport = AsyncProxyTransport.from_url(proxy)
            self.ses = httpx.AsyncClient(
                transport=transport,
                timeout=10000,
                verify=False,
                http2=False,
                trust_env=False
            )
        else:
            self.ses = cfcrawler.AsyncClient(timeout=1000)

        self.headers= {
            'Accept': 'application/json',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'DNT': '1',
            'Origin': 'https://web.pinai.tech',
            'Referer': 'https://web.pinai.tech/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
            'lang': 'zh-CN',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"'           
        }
    
    def log(self,msg):
        now = datetime.now().isoformat().split("T")[1].split(".")[0]
        print(
            f"{black}[{now}]{white}-{blue}[{white}account {self.p + 1}{blue}]{white} {msg}{reset}"
        )
    def get_random_proxy(self, isself, israndom=False):
        if israndom:
            return random.choice(self.proxies)
        return self.proxies[isself % len(self.proxies)]

    async def ipinfo(self):
        ipinfo1_url = "https://ipapi.co/json/"
        ipinfo2_url = "https://ipwho.is/"
        ipinfo3_url = "https://freeipapi.com/api/json"
        headers = {"user-agent": "marin kitagawa"}
        try:
            res = await self.http(ipinfo1_url, headers)
            ip = res.json().get("ip")
            country = res.json().get("country")
            if not ip:
                res = await self.http(ipinfo2_url, headers)
                ip = res.json().get("ip")
                country = res.json().get("country_code")
                if not ip:
                    res = await self.http(ipinfo3_url, headers)
                    ip = res.json().get("ipAddress")
                    country = res.json().get("countryCode")
            self.log(f"{green}ip : {white}{ip} {green}country : {white}{country}")
        except json.decoder.JSONDecodeError:
            self.log(f"{green}ip : {white}None {green}country : {white}None")

    async def http(self, url, headers, data=None):
        while True:
            try:
                if not await aiofiles.ospath.exists(log_file):
                    async with aiofiles.open(log_file, "w") as w:
                        await w.write("")
                logsize = await aiofiles.ospath.getsize(log_file)
                if logsize / 1024 / 1024 > 1:
                    async with aiofiles.open(log_file, "w") as w:
                        await w.write("")
                if data is None:
                    res = await self.ses.get(url, headers=headers)
                elif data == "":
                    res = await self.ses.post(url, headers=headers)
                else:
                    res = await self.ses.post(url, headers=headers, data=data)
                async with aiofiles.open(log_file, "a", encoding="utf-8") as hw:
                    await hw.write(f"{res.status_code} {res.text}\n")
                if "<title>" in res.text:
                    self.log(f"{yellow}failed get json response !")
                    await countdown(3)
                    continue

                return res
            except (
                httpx.ProxyError,
                python_socks._errors.ProxyTimeoutError,
                python_socks._errors.ProxyError,
            ):
                proxy = self.get_random_proxy(0, israndom=True)
                transport = AsyncProxyTransport.from_url(proxy)
                self.ses = httpx.AsyncClient(transport=transport)
                self.log(f"{yellow}proxy error,selecting random proxy !")
                await asyncio.sleep(3)
                continue
            except httpx.NetworkError:
                self.log(f"{yellow}network error !")
                await asyncio.sleep(3)
                continue
            except httpx.TimeoutException:
                self.log(f"{yellow}connection timeout !")
                await asyncio.sleep(3)
                continue
            except (httpx.RemoteProtocolError, anyio.EndOfStream):
                self.log(f"{yellow}connection close without response !")
                await asyncio.sleep(3)
                continue



    def is_expired(self, token):
        if token is None or isinstance(token, bool):
            return True
        header, payload, sign = token.split(".")
        payload = b64decode(payload + "==").decode()
        jload = json.loads(payload)
        now = round(datetime.now().timestamp()) + 300
        exp = jload["exp"]
        if now > exp:
            return True
        return False           

    async def login(self):
        auth_url = "https://prod-api.pinai.tech/passport/login/telegram"
        data = {
            "init_data": self.query,
        }
        res = await self.http(auth_url, self.headers, json.dumps(data))
        access_token = res.json().get("access_token")
        refresh_token = res.json().get("refresh_token")
        if not access_token:
            message = res.json().get("message", "")
            if "signature is invalid" in message:
                self.log(f"{red}data has the wrong format or data is outdated.")
                return False
            self.log(f"{red}{message}, check log file http.log !")
            return False
        uid = self.user.get("id")
        self.db.update({"access_token": access_token, "refresh_token": refresh_token}, Query().id == uid)
        self.log(f"{green}success get access token !")
        self.headers["authorization"] = f"Bearer {access_token}"
        return True
    
    async def check_in(self):
        url = "https://prod-api.pinai.tech/task/checkin_data"
        res = await self.http(url=url, headers=self.headers)
        if res.status_code != 200:
            self.log(f"{red}failed to get checkin data !")
            return False
        today_reward = res.json().get('tasks', [{}])[0].get('reward_points', {})
        is_claim = res.json().get('tasks', [{}])[0].get('checkin_detail', {}).get('is_today_checkin')
        if is_claim:
            self.log(f"{yellow}already checkin today !")
            return False
        else:
            url = "https://prod-api.pinai.tech/task/1001/v1/complete"
            res = await self.http(url=url, headers=self.headers, data="")
            if res.json().get("status") == "success":
                self.log(f"{green}success checkin today,reward : {white}{today_reward}")
                return True
            else:
                self.log(f"{red}failed checkin today !")
                return False
    
    async def collect_coin(self, coin_type, coin_count):
        url = "https://prod-api.pinai.tech/home/collect"
        payload = json.dumps([
            {
                "type": coin_type,
                "count": coin_count
            }
        ])
        res = await self.http(url=url, headers=self.headers, data=payload)
        if res.status_code == 200:
            self.log(f"{green}success collect {coin_count} {coin_type} coin !")
            return True
        else:
            self.log(f"{red}failed collect coin !")
            return False
    
    async def task(self):
        task_url = "https://prod-api.pinai.tech/task/v4/list"
        task_list = (await self.http(url=task_url, headers=self.headers)).json().get("tasks",[])
        task_name = [task.get("task_name") for task in task_list]
        task_id = [task.get("task_id") for task in task_list]
        is_complete = [task.get("is_complete") for task in task_list]
        need_claim = [task.get("need_claim") for task in task_list]
        can_claim = [task.get("can_claim") for task in task_list]
        reward_points = [task.get("reward_points") for task in task_list]
        for task_name, task_id, is_complete, need_claim, can_claim, reward_points in zip(task_name, task_id, is_complete, need_claim, can_claim, reward_points):
            if is_complete:
                self.log(f"{yellow}already complete {task_name} !")
                if can_claim:
                    url = f"https://prod-api.pinai.tech/task/{task_id}/claim"
                    res = await self.http(url=url, headers=self.headers, data=json.dumps({}))
                    if res.json().get("status") == "success":
                        self.log(f"{green} claim {task_name} points {reward_points}!")
                    else:
                        self.log(f"{red} failed claim {task_name} points!")
            else:
                if task_id in [1002, 1004]:
                    complete_url = f"https://prod-api.pinai.tech/task/{task_id}/v2/complete"
                    await self.http(url=complete_url, headers=self.headers, data=json.dumps({}))
                    await countdown(random.randint(5, 10))
                    self.log(f"{green}complete {task_name} !")
                    claim_url = f"https://prod-api.pinai.tech/task/{task_id}/claim"
                    res = await self.http(url=claim_url, headers=self.headers,data=json.dumps({}))
                    if res.json().get("status") == "success":
                        self.log(f"{green}{task_name} success claim {reward_points} points!")
                    else:
                        self.log(f"{red}{task_name} failed claim {reward_points} points!")

        random_task_url = "https://prod-api.pinai.tech/task/random_task_list"
        res = await self.http(url=random_task_url, headers=self.headers)
        is_today_done = res.json().get("is_today_done", 0)
        if is_today_done:
            self.log(f"{yellow}already done random task today !")
            return True
        else:
            random_task_list = res.json().get("tasks", [])
            if len(random_task_list) == 0:
                self.log(f"{red}no random task list !")
                return False
            task_id = [task.get("task_id") for task in random_task_list]
            need_num = [task.get("need_num") for task in random_task_list]
            is_complete = [task.get("is_complete") for task in random_task_list]
            task_name = [task.get("task_name") for task in random_task_list]
            for task_id, need_num, is_complete, task_name in zip(task_id, need_num, is_complete, task_name):
                if is_complete:
                    self.log(f"{yellow}already complete random task {task_name} !")
                else:
                    if task_name == "Use the agent Horoscope 1 times":
                        for _ in range(need_num):
                            self.log(f"{green}task id:{task_id} {task_name} !")
                            horoscope_url = "https://prod-api.pinai.tech/action/v1/horoscope"
                            await self.http(url=horoscope_url, headers=self.headers)
                            await countdown(random.randint(5, 10))
                        self.log(f"{green}complete random task :{task_name} !")
                    if task_name == "Use the Agent feature 1 times":
                        for _ in range(need_num):
                            self.log(f"{green}task id:{task_id} {task_name} !")
                            horoscope_url = "https://prod-api.pinai.tech/action/v1/horoscope"
                            await self.http(url=horoscope_url, headers=self.headers)
                            await countdown(random.randint(5, 10))
                        self.log(f"{green}complete random task :{task_name} !")
                    if task_name == "Use the Agent feature 2 times":
                        for _ in range(need_num):
                            self.log(f"{green}task id:{task_id} {task_name} !")
                            horoscope_url = "https://prod-api.pinai.tech/action/v1/horoscope"
                            await self.http(url=horoscope_url, headers=self.headers)
                            await countdown(random.randint(5, 10))
                        self.log(f"{green}complete random task :{task_name} !")
                    if task_name == "Use the Agent feature 3 times":
                        for _ in range(need_num):
                            self.log(f"{green}task id:{task_id} {task_name} !")
                            horoscope_url = "https://prod-api.pinai.tech/action/v1/horoscope"
                            await self.http(url=horoscope_url, headers=self.headers)
                            await countdown(random.randint(5, 10))
                        self.log(f"{green}complete random task :{task_name} !")
                    if task_id == 1014:
                        if task_name == "Use the agent Shopping 1 times":
                            self.log(f"{green} Use the agent Shopping 1 times!")
                            url = "https://prod-api.pinai.tech/action/steps?action_id=2003&name=Phone+chargers+and+cables&category=Phone+chargers+and+cables"
                            await self.http(url=url, headers=self.headers, data=json.dumps({}))
                        if task_name == "Use the agent X Insights 1 times":
                            self.log(f"{green} Use the agent X Insights 1 times!")
                            url = "https://prod-api.pinai.tech/action/friends/summary/twitter?user_name=weikaide"
                            await self.http(url=url, headers=self.headers)
                            await countdown(random.randint(5, 10))
                            self.log(f"{green}complete random task :{task_name} !")
                        if task_name == "Use the agent Ask for rides 2 times":
                            self.log(f"{green} Use the agent Ask for rides 2 times!")
                            url = "https://prod-api.pinai.tech/action/steps?action_id=2004&name=Uber&category=Uber"
                            await self.http(url=url, headers=self.headers, data=json.dumps({}))
                            await countdown(random.randint(5, 10))
                            self.log(f"{green}complete random task :{task_name} !")
                    if task_id == 1011:
                        if task_name == "3 data accounts have been connected":
                            self.log(f"{red} need to connected 3 data accounts")
                            return False
                        if task_name == "2 data accounts have been connected":
                            self.log(f"{red} need to connected 2 data accounts")
                            return False
                    if task_id == 1012:
                        self.log(f"{red} need to connect Facebook data account")
                        return False
                    if task_id == 1015:
                        self.log(f"{red} need to join a community")
                        url = "https://prod-api.pinai.tech/community/join"
                        res = await self.http(url=url, headers=self.headers, data=json.dumps({"tg_group_link":"https://t.me/HiPIN_RU"}))
                        if res.json().get("role",0) == "member":
                            self.log(f"{green} success join a community!")
                            url = "https://prod-api.pinai.tech/community/1/claim"
                            res = await self.http(url=url, headers=self.headers, data=json.dumps({}))
                            if res.json().get("status") == "success":
                                self.log(f"{green} success claim community points!")
                            else:
                                self.log(f"{red} failed claim community points!")
                        else:
                            self.log(f"{red} failed join a community!")
                        return False
                    if task_id == 1016:
                        self.log(f"{red} need to connect 4 data accounts")
                        return False

            res = await self.http(url=random_task_url, headers=self.headers)
            if res.json().get("can_claim") and (res.json().get("is_today_done") == False):
                url = "https://prod-api.pinai.tech/task/claim_random_task"
                res = await self.http(url=url, headers=self.headers)
                if res.json().get("status") == "success":
                    total_reward_points = res.json().get("total_reward_points")
                    self.log(f"{green}success claim random task points {total_reward_points}!")
                    return True
                else:
                    self.log(f"{red}failed claim random task points!")
                    return False
            if not res.json().get("can_claim") and (res.json().get("is_today_done") == False):
                self.log(f"{red} can't claim points, still have incomplete random task!")
                return False
            else:
                self.log(f"{red} can't claim points!")
                return False

    async def start(self):
        #随机等待1-10秒
        await countdown(random.randint(1, 10))
        #如果数据无效，则返回当前时间戳+8小时
        if not self.valid:
            self.log(f"{red}data is invalid !")
            return int(datetime.now().timestamp())+(3600*8)
        #主页数据
        home_url = "https://prod-api.pinai.tech/home"
        #打印ip信息
        if len(self.proxies) > 0:
            await self.ipinfo()
        #获取用户id
        uid = self.user.get("id")
        #获取用户名
        first_name = self.user.get("first_name")
        #获取用户姓
        last_name = self.user.get("last_name")
        #获取用户数据
        result = self.db.search(Query().id == uid)
        #如果用户数据不存在，则创建用户数据
        if len(result) == 0:
            #创建默认用户数据
            self.db.insert(
                {
                    "id": uid,
                    "first_name": first_name,
                    "last_name": last_name,
                    "access_token": None,
                    "refresh_token": None,
                    "pin_points_in_number": 0,
                    "data_power": 0,
                    "last_login": int(datetime.now().timestamp()),
                    "level": 0,
                }
            )
            result = self.db.search(Query().id == uid)
        #获取上次登录时间
        last_login = result[0].get("last_login")
        #获取用户等级
        level = result[0].get("level")
        #打印用户信息
        self.log(f"{green}login as {first_name}{last_name} uid:{uid} level:{level}")
        #获取当前时间戳
        timestamp = int(datetime.now().timestamp())
        #更新上次登录时间
        self.db.update({"last_login": timestamp}, Query().id == uid)
        #打印上次登录时间
        self.log(f"{green}last login : {white}{datetime.fromtimestamp(last_login)}")
        #获取access token
        access_token = result[0].get("access_token")
        #获取access token是否过期
        expired = self.is_expired(access_token)
        #如果access token过期，则重新登录
        if expired:
            self.log(f"{yellow}access token expired, renewing access token...")
            result = await self.login()
            if not result:
                self.log(f"{red}failed to renew access token !")
                #返回当前时间戳+300秒后重试
                return int(datetime.now().timestamp())+300
        else:
            self.headers["authorization"] = f"Bearer {access_token}"
        #如果自动签到，则签到
        if self.cfg.auto_checkin:
            await self.check_in()
        #获取主页数据
        res = await self.http(home_url, self.headers)
        if res.status_code != 200:
            self.log(f"{red}failed to get home data !")
            return False
        #获取PIN POINTS和DATA POWER
        pin_points_in_number = res.json().get("pin_points_in_number", 0)
        data_power = res.json().get("data_power", 0)
        level = res.json().get("current_model", {}).get("current_level", 0)

        #打印PIN POINTS和DATA POWER
        self.log(f"{green}PIN POINTS     : {white}{pin_points_in_number}")
        self.log(f"{green}DATA POWER     : {white}{data_power}")
        self.log(f"{green}LEVEL          : {white}{level}")
        #如果自动收集硬币，则收集硬币
        if self.cfg.auto_collect:
            self.log(f"{green} Collecting coin...")
            coin_list = [coin.get("type", "") for coin in res.json().get("coins", [])]
            coin_count = [coin.get("count", 0) for coin in res.json().get("coins", [])]
            while any(coin_count):
                for coin_type, count in zip(coin_list, coin_count):
                    if count > 0:
                        await self.collect_coin(coin_type=coin_type, coin_count=count)
                        await countdown(random.randint(3, 10))
                res = await self.http(home_url, self.headers)
                if res.status_code != 200:
                    self.log(f"{red}failed to get home data !")
                    return False
                coin_count = [coin.get("count", 0) for coin in res.json().get("coins", [])]
            self.log(f"{green}all coin collected !")
        #如果自动任务，则执行任务
        if self.cfg.auto_task:
            self.log(f"{green} Start to complete task...")
            await self.task()
        #如果自动升级，则升级
        if self.cfg.auto_upgrade:
            self.log(f"{green} Start upgrade...")
            res = await self.http(home_url, self.headers)
            pin_points_in_number = res.json().get("pin_points_in_number", 0)
            cost = res.json().get("cost", 0)
            if pin_points_in_number > 0 and cost > 0:
                while pin_points_in_number >= cost :
                    upgrade_url = "https://prod-api.pinai.tech/model/upgrade"
                    res = await self.http(url=upgrade_url, headers=self.headers, data=json.dumps({}))
                    if res.status_code == 200:
                        level = res.json().get("current_model", {}).get("current_level", 0)
                        self.log(f"{green}success upgrade to level {level} !")
                    else:
                        self.log(f"{red}failed upgrade !")
                        return False
                    res = await self.http(home_url, self.headers)
                    pin_points_in_number = res.json().get("pin_points_in_number", 0)
                    cost = res.json().get("cost", 0)
                    await countdown(random.randint(5, 10))
                self.log(f"{green} upgrade completed !")

        # 获取最新的数据
        res = await self.http(home_url, self.headers)
        if res.status_code != 200:
            self.log(f"{red}failed to get home data !")
            return False
        #获取PIN POINTS和DATA POWER
        pin_points_in_number = res.json().get("pin_points_in_number", 0)
        data_power = res.json().get("data_power", 0)
        level = res.json().get("current_model", {}).get("current_level", 0)
        #更新用户数据
        self.db.update({"pin_points_in_number": pin_points_in_number}, Query().id == uid)
        self.db.update({"data_power": data_power}, Query().id == uid)
        self.db.update({"level": level}, Query().id == uid)
        #打印PIN POINTS和DATA POWER
        self.log(f"{green}PIN POINTS     : {white}{pin_points_in_number}")
        self.log(f"{green}DATA POWER     : {white}{data_power}")
        self.log(f"{green}LEVEL          : {white}{level}")
        #返回当前时间戳+4小时后重试 
        wait_period = int(datetime.now().timestamp())+3600*4
        return round(wait_period)
        
async def get_data(data_file, proxy_file):
    async with aiofiles.open(data_file) as w:
        read = await w.read()
        datas = [i for i in read.splitlines() if len(i) > 10]
    async with aiofiles.open(proxy_file) as w:
        read = await w.read()
        proxies = [i for i in read.splitlines() if len(i) > 5]
    return datas, proxies

async def countdown(t):
    for i in range(t, 0, -1):
        minute, seconds = divmod(i, 60)
        hour, minute = divmod(minute, 60)
        seconds = str(seconds).zfill(2)
        minute = str(minute).zfill(2)
        hour = str(hour).zfill(2)
        print(f"waiting for {hour}:{minute}:{seconds} ", flush=True, end="\r")
        await asyncio.sleep(1)

async def main():
    banner = f"""
{magenta}██╗    ██╗███████╗██╗██╗  ██╗ █████╗ ██╗██████╗ ███████╗
{magenta}██║    ██║██╔════╝██║██║ ██╔╝██╔══██╗██║██╔══██╗██╔════╝
{magenta}██║ █╗ ██║█████╗  ██║█████╔╝ ███████║██║██║  ██║█████╗  
{magenta}██║███╗██║██╔══╝  ██║██╔═██╗ ██╔══██║██║██║  ██║██╔══╝  
{magenta}╚███╔███╔╝███████╗██║██║  ██╗██║  ██║██║██████╔╝███████╗
{magenta} ╚══╝╚══╝ ╚══════╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═════╝ ╚══════╝
"""
    arg = argparse.ArgumentParser()
    arg.add_argument(
        "--data",
        "-D",
        default=data_file,
        help=f"Perform customer input for data file (default: {data_file})",
    )
    arg.add_argument(
        "--action",
        "-A",
        help="Function to directly enter the menu without displaying input",
    )
    arg.add_argument(
        "--proxy",
        "-P",
        default=proxy_file,
        help=f"Perform custom input for proxy files (default : {proxy_file})",
    )
    arg.add_argument(
        "--worker",
        "-W",
        help=f"Perform custom input for worker (default : cpu core -1 )",
    )
    arg.add_argument("--marin", action="store_true")
    args = arg.parse_args()
    if not await aiofiles.ospath.exists(args.data):
        async with aiofiles.open(args.data, "a") as w:
            pass
    if not await aiofiles.ospath.exists(args.proxy):
        async with aiofiles.open(args.proxy, "a") as w:
            pass
    if not await aiofiles.ospath.exists(config_file):
        async with aiofiles.open(config_file, "w") as w:
            _config = {
                "auto_checkin": True,
                "auto_collect": True,
                "auto_task": True,
                "auto_upgrade": True,
            }
            await w.write(json.dumps(_config, indent=4))
    while True:
        if not args.marin:
            os.system("cls" if os.name == "nt" else "clear")
        print(banner)
        async with aiofiles.open(config_file) as r:
            read = await r.read()
            cfg = json.loads(read)
            config = Config(
                auto_checkin=cfg.get("auto_checkin"),
                auto_collect=cfg.get("auto_collect"),
                auto_task=cfg.get("auto_task"),
                auto_upgrade=cfg.get("auto_upgrade"),
            )
        datas, proxies = await get_data(data_file=args.data, proxy_file=args.proxy)
        menu = f"""
{white}data file :{green} {args.data}
{white}proxy file :{green} {args.proxy}
{green}total data :{white} {len(datas)}
{green}total proxy :{white} {len(proxies)}

    {green}1{white}.{green}) {white}set on/off auto checkin ({(green + "active" if config.auto_checkin else red + "non-active")})
    {green}2{white}.{green}) {white}set on/off auto collect coin({(green + "active" if config.auto_collect else red + "non-active")})
    {green}3{white}.{green}) {white}set on/off auto task({(green + "active" if config.auto_task else red + "non-active")})
    {green}4{white}.{green}) {white}set on/off auto upgrade({(green + "active" if config.auto_upgrade else red + "non-active")})
    {green}5{white}.{green}) {white}start bot (sync mode)
    {green}6{white}.{green}) {white}start bot (multi-thread mode)
        """
        opt = None
        if args.action:
            opt = arg.action
        else:
            print(menu)
            opt = input(f"{green}input number : {white}")
            print(f"{white}~" * 50)
        if opt == "1":
            cfg["auto_checkin"] = False if config.auto_checkin else True
            async with aiofiles.open(config_file, "w") as w:
                await w.write(json.dumps(cfg, indent=4))
            print(f"{green}success update auto_checkin config")
            input(f"{blue}press enter to continue")
            opt = None
            continue
        if opt == "2":
            cfg["auto_collect"] = False if config.auto_collect else True
            async with aiofiles.open(config_file, "w") as w:
                await w.write(json.dumps(cfg, indent=4))
            print(f"{green}success update auto_collect config !")
            input(f"{blue}press enter to continue")
            opt = None
            continue
        if opt == "3":
            cfg["auto_task"] = False if config.auto_task else True
            async with aiofiles.open(config_file, "w") as w:
                await w.write(json.dumps(cfg, indent=4))
            print(f"{green}success update auto_task config !")
            input(f"{blue}press enter to continue")
            opt = None
            continue
        if opt == "4":
            cfg["auto_upgrade"] = False if config.auto_upgrade else True
            async with aiofiles.open(config_file, "w") as w:
                await w.write(json.dumps(cfg, indent=4))
            print(f"{green}success update auto_upgrade config !")
            input(f"{blue}press enter to continue")
            opt = None
            continue
        if opt == "5":
            while True:
                datas, proxies = await get_data(args.data, args.proxy)
                result = []
                for no, data in enumerate(datas):
                    res = await PIN_AI(
                        id=no, query=data, proxies=proxies, config=config
                    ).start()
                    result.append(res)
                await countdown(3600*3)
        if opt == "6":
            if not args.worker:
                worker = int(os.cpu_count()-1)
                print(f"{green}available worker : {worker}")
                if worker < 1:
                    worker = 1
            else:
                worker = int(args.worker)
            sema = asyncio.Semaphore(worker)

            async def bound(sema, params):
                async with sema:
                    return await PIN_AI(*params).start()

            while True:
                datas, proxies = await get_data(args.data, args.proxy)
                tasks = [
                    asyncio.create_task(bound(sema, (no, data, proxies, config)))
                    for no, data in enumerate(datas)
                ]
                result = await asyncio.gather(*tasks)
                end = int(datetime.now().timestamp())
                total = min(result) - end
                await countdown(total)
        if opt == None:
            continue

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        exit()
