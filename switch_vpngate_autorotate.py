#!/usr/bin/env python3
# switch_vpngate.py (v2.7 auto-rotate)
# ✅ 自动每10分钟切换VPN出口，安全模式，不改全局路由

import os
import subprocess
import base64
import random
import time
import requests
import csv
import sys
import json
import re
import signal

POOL_FILE = "/opt/vpngate_pool.csv"
LOG_FILE = "/var/log/vpngate_autorotate.log"
OVPN_FILE = "/opt/vpngate_current.ovpn"
OVPN_LOG_FILE = "/var/log/openvpn_client.log"
PID_FILE = "/var/run/vpngate_switch.pid"

ROTATE_INTERVAL = 600  # 每10分钟切换一次
WAIT_LOG_READY = 10
MAX_VERIFY_TRIES = 5

def log(msg):
    t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"[{t}] {msg}")
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{t}] {msg}\n")
    except Exception:
        pass

def get_current_ip():
    try:
        r = requests.get("https://ipinfo.io/json", timeout=8)
        if r.status_code == 200:
            return r.json().get("ip")
    except:
        pass
    return None

def detect_tun_interface():
    try:
        out = subprocess.check_output(["ip", "link"], text=True)
        m = re.findall(r"(tun\d+):", out)
        if m:
            return m[0]
    except:
        pass
    return "tun0"

def stop_old_vpn():
    subprocess.run(["pkill", "-f", "openvpn --config"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

def safe_write_config(cfg_decoded, cipher):
    with open(OVPN_FILE, "w") as f:
        f.write(cfg_decoded.strip() + "\n")
        f.write("# --- auto generated safe config ---\n")
        f.write(f"cipher {cipher}\n")
        f.write(f"data-ciphers AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305:{cipher}\n")
        # 安全模式：不全局路由
        f.write("pull-filter ignore redirect-gateway\n")
        f.write("route-nopull\n")
        if os.path.exists("/etc/openvpn/update-resolv-conf"):
            f.write("script-security 2\n")
            f.write("up /etc/openvpn/update-resolv-conf\n")
            f.write("down /etc/openvpn/update-resolv-conf\n")
        f.write(f"log {OVPN_LOG_FILE}\nwritepid {PID_FILE}\n")

def connect_and_verify(server):
    ip = server.get("IP")
    country = server.get("CountryLong", "Unknown")
    cfg64 = server.get("OpenVPN_ConfigData_Base64")
    if not cfg64:
        return False
    try:
        cfg_decoded = base64.b64decode(cfg64).decode("utf-8", errors="ignore")
    except:
        log(f"Base64解码失败: {ip}")
        return False

    cipher_line = re.search(r"cipher\s+([A-Za-z0-9-]+)", cfg_decoded)
    cipher = cipher_line.group(1) if cipher_line else "AES-128-CBC"

    safe_write_config(cfg_decoded, cipher)

    log(f"启动 OpenVPN 节点 {ip} ({country}) ...")
    open(OVPN_LOG_FILE, "w").close()
    subprocess.Popen(["openvpn", "--config", OVPN_FILE, "--daemon"])
    time.sleep(WAIT_LOG_READY)

    # 等待初始化
    for _ in range(10):
        try:
            txt = open(OVPN_LOG_FILE).read()
            if "Initialization Sequence Completed" in txt:
                break
        except:
            pass
        time.sleep(2)

    tun = detect_tun_interface()
    log(f"检测到接口: {tun}")

    orig_ip = get_current_ip()
    for n in range(MAX_VERIFY_TRIES):
        time.sleep(5)
        try:
            result = subprocess.run(
                ["curl", "-s", "--interface", tun, "--connect-timeout", "8", "https://ipinfo.io/json"],
                capture_output=True, text=True, timeout=15)
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                vpn_ip = data.get("ip")
                if vpn_ip and vpn_ip != orig_ip:
                    log(f"✅ 出口切换成功: {vpn_ip} ({data.get('country')}) via {ip} [{country}]")
                    return True
                else:
                    log(f"IP未改变 (仍为 {vpn_ip})，重试中...")
        except Exception as e:
            log(f"验证异常: {e}")
    log("❌ 验证失败。停止节点。")
    stop_old_vpn()
    return False

def signal_handler(sig, frame):
    log("收到中断信号，正在清理并退出...")
    stop_old_vpn()
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        with open(POOL_FILE, newline='', encoding='utf-8') as f:
            servers = list(csv.DictReader(f))
    except Exception as e:
        log(f"读取节点池失败: {e}")
        sys.exit(1)

    random.shuffle(servers)
    log(f"共加载 {len(servers)} 个节点，开始自动轮换...")

    index = 0
    while True:
        stop_old_vpn()
        server = servers[index % len(servers)]
        if connect_and_verify(server):
            log(f"🌐 当前节点运行中，将在 {ROTATE_INTERVAL//60} 分钟后自动切换...")
            time.sleep(ROTATE_INTERVAL)
        else:
            log("节点连接失败，立即尝试下一个。")
            time.sleep(5)
        index += 1

if __name__ == "__main__":
    main()
