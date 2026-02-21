import pdfplumber
import pandas as pd
import os
import re
from tqdm import tqdm

def get_folder():
    while True:
        folder = input("请输入发票文件夹路径（可直接拖入文件夹）：\n> ").strip('"').strip()

        if os.path.isdir(folder):
            return folder
        else:
            print("路径不存在，请重新输入！\n")

def find_company_by_taxid(lines, taxid):
    """根据税号反推公司名称（税号上一行通常是公司名）"""
    for i, line in enumerate(lines):
        if taxid in line and i > 0:
            name_line = lines[i-1].strip()

            # 去掉一些无效标题行
            if len(name_line) > 4 and "税务" not in name_line and "监制" not in name_line:
                return name_line
    return ""

def extract_info(pdf_path):
    info = {
        "文件名": os.path.basename(pdf_path),
        "发票代码": "",
        "发票号码": "",
        "开票日期": "",
        "金额": "",
        "购买方名称": "",
        "购买方税号": ""
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t

        lines = text.split('\n')

        # 发票代码
        code = re.search(r'发票代码[:：]?\s*(\d{10,12})', text)
        if code:
            info["发票代码"] = code.group(1)

        # 发票号码
        number = re.search(r'发票号码[:：]?\s*(\d{8,20})', text)

        if not number:
            number = re.search(r'(\b\d{20}\b)', text)

        if number:
            info["发票号码"] = number.group(1)

        # 日期
        date = re.search(r'(\d{4}年\d{2}月\d{2}日)', text)
        if date:
            info["开票日期"] = date.group(1)

        # 金额
        amount = re.search(r'价税合计.*?([0-9]+\.[0-9]{2})', text)
        if amount:
            info["金额"] = amount.group(1)

        # ===== 购买方、销售方识别 =====
        # 找18位统一社会信用代码
        tax_ids = re.findall(r'\b[0-9A-Z]{18}\b', text)

        if len(tax_ids) >= 2:
            buyer_taxid = tax_ids[0]
            seller_taxid = tax_ids[1]

            info["购买方税号"] = buyer_taxid
            info["销售方税号"] = seller_taxid

            # # 根据税号反查公司名称
            # info["购买方名称"] = find_company_by_taxid(lines, buyer_taxid)
            # info["销售方名称"] = find_company_by_taxid(lines, seller_taxid)

    except Exception as e:
        print("读取失败:", pdf_path, e)

    return info


def main():
    print("====== 发票自动查重工具 ======\n")

    # 由用户输入目录
    FAPIAO_DIR = get_folder()

    pdf_files = [f for f in os.listdir(FAPIAO_DIR) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print("该目录下没有PDF发票！")
        return

    result = []

    for file in tqdm(pdf_files, desc="扫描发票"):
        path = os.path.join(FAPIAO_DIR, file)
        info = extract_info(path)
        result.append(info)

    df = pd.DataFrame(result)

    # 查重
    df["是否重复"] = df.duplicated(subset=["发票代码", "发票号码"], keep=False)

    # 排序
    df.sort_values(by=["是否重复", "发票代码"], ascending=False, inplace=True)

    # 输出Excel到同目录
    out_file = os.path.join(FAPIAO_DIR, "发票查重结果.xlsx")
    df.to_excel(out_file, index=False)

    print("\n完成！")
    print("结果文件：", out_file)
    input("\n按回车键退出...")

if __name__ == "__main__":
    main()