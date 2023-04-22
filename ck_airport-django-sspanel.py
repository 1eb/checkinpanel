# -*- coding: utf-8 -*-
"""
django-sspanel 机场签到，基于share.cjy.me，其他站点未测试
:author @Icrons @1eb
cron: 20 7 * * *
new Env('机场签到(django-sspanel)');
"""

import json
import re
import traceback

import requests
import urllib3

from notify_mtr import send
from utils import get_data

urllib3.disable_warnings()


class SspanelQd:
    def __init__(self, check_items):
        self.check_items = check_items

    @staticmethod
    def checkin(url, email, password):
        url = url.rstrip("/")
        emails = email.split("@")
        email = f"{emails[0]}%40{emails[1]}" if len(emails) > 1 else emails[0]
        session = requests.session()

        # 以下 except 都是用来捕获当 requests 请求出现异常时，
        # 通过捕获然后等待网络情况的变化，以此来保护程序的不间断运行
        try:
            session.get(url, verify=False)
        except requests.exceptions.ConnectionError:
            return f"{url}\n网络不通"
        except requests.exceptions.ChunkedEncodingError:
            return f"{url}\n分块编码错误"
        except Exception:
            print(f"未知错误，错误信息：\n{traceback.format_exc()}")
            return f"{url}\n未知错误，请查看日志"

        login_url = f"{url}/login/"

        #  获取登录页csrfmiddlewaretoken
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/112.0.0.0 Safari/537.36",
        }

        try:
            response = session.get(login_url, headers=headers, verify=False)
            #正则提取csrfmiddlewaretoken
            csrfmiddlewaretoken = re.findall('<input type="hidden" name="csrfmiddlewaretoken" value="(.*?)">', response.text)[0]
            print(f"{url} 获取登录页csrfmiddlewaretoken：{csrfmiddlewaretoken}")
        except Exception:
            print(f"获取登录页csrfmiddlewaretoken失败，错误信息：\n{traceback.format_exc()}")
            return f"{url}\n获取登录页csrfmiddlewaretoken失败，请查看日志"

    
        #登录
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/112.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": f"{url}/login/",
        }
        login_data = f"csrfmiddlewaretoken={csrfmiddlewaretoken}&username={email}&password={password}".encode()

        try:
            response = session.post(
                login_url, login_data, headers=headers, verify=False, allow_redirects=False
            )
            if response.status_code == 302:
                print(f"{url} 登录成功")
            else:
                return f"{url} 登录失败\nSTATUS_CODE: {response.status_code}\nHEADER: {response.headers.items()}\n{response.cookies.items()}"
        except Exception:
            print(f"登录失败，错误信息：\n{traceback.format_exc()}")
            return f"{url}\n登录失败，请查看日志"
        
        # 用户信息页获取签到csrf
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/112.0.0.0 Safari/537.36",
            "Referer": f"{url}/login/",
        }
        info_url = f"{url}/users/userinfo/"

        try:
            response = session.get(info_url, headers=headers, verify=False)
            csrfmiddlewaretoken = re.findall(r'csrfmiddlewaretoken\: \'(.*?)\',', response.text)[0]
            print(f"{url} 获取签到csrfmiddlewaretoken：{csrfmiddlewaretoken}")
        except Exception:
            print(f"获取签到csrfmiddlewaretoken失败，错误信息：\n{traceback.format_exc()}")
            return f"{url}\n获取签到csrfmiddlewaretoken失败，请查看日志"


        #签到
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/112.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": f"{url}/users/userinfo/",
        }
        checkin_url = f"{url}/api/checkin/"
        checkin_data = f"csrfmiddlewaretoken={csrfmiddlewaretoken}".encode()
        try:
            response = session.post(
                checkin_url, checkin_data, headers=headers, verify=False, allow_redirects=False
            )
            sign_text = response.text
            print(f"{url} 接口签到返回信息：{sign_text}")
            sign_json = json.loads(sign_text)
            sign_msg = sign_json.get("title") + sign_json.get("subtitle")
            if sign_json.get("status") == "success":
                msg = f"{url} 签到成功\n{sign_msg}"
            else:
                msg = f"{url} 签到失败\n{sign_msg}"
        except Exception:
            msg = f"{url}\n签到失败失败，请查看日志"
            print(f"签到失败，错误信息：\n{traceback.format_exc()}")

        # 获取用户信息
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/112.0.0.0 Safari/537.36",
            "Referer": f"{url}/login/",
        }
        info_url = f"{url}/users/userinfo/"
        try:
            temporary_traffic = re.findall(
                r'\<li\>时效流量:\s+\<code\>(.*?)\<\/code\>', response.text)[0]
            eternal_traffic = re.findall(
                r'\<li\>永久流量:\s+\<code\>(.*?)\<\/code\>', response.text)[0]
            bonus = re.findall(r'\<li\> 魔力值：\s+\<code\>(.*?)\<\/code\>', response.text)[0]
            level = re.findall(r'\<li\> 用户组：\s+\<code\>(.*?)\<\/code\>', response.text)[0]
            exp_time = re.findall(r'\<li\> 贵宾到期时间：\s+\<code\>(.*?)\<\/code\>', response.text)[0]

            return (
                f"{url}\n"
                f"- 今日签到信息：{msg}\n"
                f"- 用户等级：{level}\n"
                f"- 到期时间：{exp_time}\n"
                f"- 时效流量：{temporary_traffic}\n"
                f"- 永久流量：{eternal_traffic}\n"
                f"- 魔力值：{bonus}"
            )
        except Exception:
            return msg
        

    def main(self):
        msg_all = ""
        for check_item in self.check_items:
            # 机场地址
            url = str(check_item.get("url"))
            # 登录信息
            email = str(check_item.get("email"))
            password = str(check_item.get("password"))
            if url and email and password:
                msg = self.checkin(url, email, password)
            else:
                msg = "配置错误"
            msg_all += msg + "\n\n"
        return msg_all


if __name__ == "__main__":
    _data = get_data()
    _check_items = _data.get("AIRPORT-DJANGO", [])
    res = SspanelQd(check_items=_check_items).main()
    send("机场签到", res)
