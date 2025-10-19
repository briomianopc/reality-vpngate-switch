#!/usr/bin/env python3
# fetch_vpngate.py (v2.1 auto)
# 在原版基础上增加 24 小时自动刷新机制

import requests
import csv
import io
import sys
import time

API_URL = "http://www.vpngate.net/api/iphone/"
POOL_FILE = "/opt/vpngate_pool.csv"
MIN_SCORE = 1000000  # 最低分数线
INTERVAL = 86400     # 24小时（秒）

def fetch_and_save_pool():
    print(f"正在从 VPNGate API 获取节点列表 (只保留分数 > {MIN_SCORE} 的节点)...")
    try:
        res = requests.get(API_URL, timeout=10)
        res.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"错误: 无法连接到VPNGate API。{e}")
        sys.exit(1)

    data = res.text.replace("\r", "")
    lines = data.split("\n")

    if len(lines) < 3:
        print("错误: 从API获取的数据无效（行数不足）。")
        return

    try:
        csv_data_file = io.StringIO("\n".join(lines[1:]))
        reader = csv.DictReader(csv_data_file)
        header = reader.fieldnames

        if not header or not header[0].startswith('#'):
            print("错误: 未找到预期的CSV表头。")
            return

        ovpn_servers = []
        for row in reader:
            try:
                if (row['OpenVPN_ConfigData_Base64'] and
                    int(row.get('Score', 0)) > MIN_SCORE):
                    ovpn_servers.append(row)
            except (ValueError, TypeError):
                continue

    except Exception as e:
        print(f"错误: 解析CSV数据时出错。{e}")
        return

    if not ovpn_servers:
        print(f"未找到分数高于 {MIN_SCORE} 的有效OpenVPN节点。")
        return

    print(f"成功获取到 {len(ovpn_servers)} 个高质量节点 (分数 > {MIN_SCORE})。")

    try:
        with open(POOL_FILE, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            writer.writerows(ovpn_servers)
        print(f"节点池已保存到 {POOL_FILE}")
    except IOError as e:
        print(f"错误: 无法写入节点池文件。{e}")

def main():
    while True:
        print("="*60)
        print(time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime()), "开始更新节点池...")
        fetch_and_save_pool()
        print("更新完成，将在24小时后再次运行。")
        print("="*60)
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
