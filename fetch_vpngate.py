#!/usr/bin/env python3
# fetch_vpngate.py (改进版 v2)
# 增加分数(Score)过滤，只保留高质量节点

import requests
import csv
import io
import sys

API_URL = "http://www.vpngate.net/api/iphone/"
POOL_FILE = "/opt/vpngate_pool.csv"
MIN_SCORE = 1000000  # 设定一个最低分数线 (可根据需要调整)

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
        sys.exit(1)

    try:
        csv_data_file = io.StringIO("\n".join(lines[1:]))
        # --- 使用 DictReader 来方便地通过列名访问 ---
        reader = csv.DictReader(csv_data_file)
        header = reader.fieldnames
        
        if not header or not header[0].startswith('#'):
             print("错误: 未找到预期的CSV表头。")
             sys.exit(1)

        ovpn_servers = []
        for row in reader:
            try:
                # 检查节点是否有效 
                if (row['OpenVPN_ConfigData_Base64'] and 
                    int(row.get('Score', 0)) > MIN_SCORE):
                    ovpn_servers.append(row)
            except (ValueError, TypeError):
                # 忽略分数无效的行
                continue
                
    except Exception as e:
        print(f"错误: 解析CSV数据时出错。{e}")
        sys.exit(1)

    if not ovpn_servers:
        print(f"未找到分数高于 {MIN_SCORE} 的有效OpenVPN节点。")
        sys.exit(0)

    print(f"成功获取到 {len(ovpn_servers)} 个高质量节点 (分数 > {MIN_SCORE})。")

    try:
        with open(POOL_FILE, "w", newline='', encoding='utf-8') as f:
            # --- 使用 DictWriter 写入 ---
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()      # 写入表头
            writer.writerows(ovpn_servers) # 写入所有节点数据
        print(f"节点池已保存到 {POOL_FILE}")
    except IOError as e:
        print(f"错误: 无法写入节点池文件。{e}")
        sys.exit(1)

if __name__ == "__main__":
    fetch_and_save_pool()
