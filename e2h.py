# coding=utf-8
import argparse
import os
import re
import time
import numpy as np
import pandas as pd
import json
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from tabulate import tabulate

html_file_path = ""


def read_html(html_file):
    global html_file_path
    html_file_data = open(html_file, "r", encoding="utf8")
    # Reading the file
    html_file_path = os.path.realpath(html_file_data.name)

    index = html_file_data.read()
    soup = BeautifulSoup(index, 'html.parser')

    json_val = list()

    for tag in soup.find_all('a'):
        json_val.append(tag.attrs)

    return json_val


def compare(excel_file, html_file):
    # excel_file_data = pd.read_excel(excel_file, sheet_name='FINAL', engine='openpyxl')
    # excel_file_data['_label'] = excel_file_data['Unnamed: 7'].str.replace("\"", "")
    # excel_file_data['_category'] = excel_file_data['Unnamed: 2'].str.replace("\"", "")
    # excel_file_data.drop(columns=['Unnamed: 7', 'Unnamed: 2'], inplace=True)

    excel_file_data = pd.read_excel(excel_file, header=None, sheet_name='FINAL', usecols=[3, 10, 13],
                                    names=['_category', '_label', 'href'], engine='openpyxl', skiprows=2)
    pd.set_option('display.max_colwidth', 1000)

    # Extracting urls,email,tel in column 'Unnamed: 10'
    pattern = r'(?:tbd|zet|mailto|tel|#|www|http)[://]?\S+[\s]?.*'
    # t_df = pd.DataFrame(excel_file_data, columns=['_label', 'Unnamed: 10'])
    # href = t_df['Unnamed: 10'].apply(lambda x: re.findall(pattern, x, re.IGNORECASE)).str
    href = excel_file_data['href'].apply(lambda x: re.findall(pattern, x, re.IGNORECASE)).str
    excel_file_data['_category'] = excel_file_data['_category'].str.replace("\"", "")
    excel_file_data['_label'] = excel_file_data['_label'].str.replace("\"", "")
    excel_file_data['href'] = href[0]

    excel_df = pd.DataFrame(excel_file_data, columns=['_label', '_category', 'href'])
    excel_df = excel_df.drop([0, 0])
    excel_df = excel_df.sort_values('_label')


    # html json to data frame
    j = json.loads(json.dumps(read_html(html_file)))
    html_df = pd.DataFrame(j, columns=['_label', '_category', 'href'])
    html_df = html_df.sort_values('_label')
    # , index=excel_df.index.copy())

    html_df['from'] = "actual"
    excel_df['from'] = "expected"

    try:
        html_df = html_df[~html_df['href'].str.contains("Zeta")]
        html_df = html_df[~html_df['href'].str.contains("tbd")]
        html_df = html_df.drop_duplicates(keep="first")

        excel_df = excel_df[~excel_df['href'].astype(str).str.contains("Zeta")]
        excel_df = excel_df[~excel_df['href'].astype(str).str.contains("tbd")]
        excel_df = excel_df.drop_duplicates(keep="first")
    except TypeError:
        print()

    df_result = pd.concat([excel_df, html_df]).drop_duplicates(['_label', '_category', 'href'], keep=False)
    df_success = pd.concat([excel_df, html_df])
    df_success = df_success[df_success.duplicated(subset=['_label', '_category', 'href'], keep=False)]
    df_success = pd.DataFrame(df_success, columns=['from', '_label', '_category', 'href'])
    df_success = df_success.sort_values('_label')

    # df_result = df_result.sort_values('description')
    df_result['result'] = np.where((df_result['_label'].eq(df_result['_label'].shift(-1)) &
                                    (df_result['_category'].eq(df_result['_category'].shift(-1))) &
                                    (df_result['href'].eq(df_result['href'].shift(-1)))), "True",
                                   np.where(df_result['from'].eq('expected'), "N/A", "False"))

    df_final = pd.DataFrame(df_result, columns=['from', '_label', '_category', 'href', 'result'])
    df_final = df_final.sort_values(['_label'], ascending=[False])
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

    file = os.path.basename(html_file)
    filepath = Path(f'{os.getcwd()}/logs/{file.split(".")[0]}-{int(time.time())}.txt')
    filepath.parent.mkdir(parents=True, exist_ok=True)

    log_msg = f"{dt_string}\n"
    log_msg += f"Found {len(df_final[df_final['from'] == 'expected'])} " \
               f"discrepancies from {html_file_path}. Please see the output below.\n"
    log_msg += tabulate(df_final, showindex=False, headers=['From', '_LABEL', '_CATEGORY', 'HREF', 'Result'])

    log_msg += "\n----------------------------------------------------------------------------\n"
    log_msg += f"\n Passed Rows: {len(df_success[df_success['from'] == 'expected'])} \n"
    log_msg += tabulate(df_success, showindex=False, headers=['From', '_LABEL', '_CATEGORY', 'HREF'])
    print(log_msg)

    with open(filepath, "w") as f:
        f.write(log_msg)

    print(f"Successfully created log file in {filepath}")


def main():
    global html_file_path
    parser = argparse.ArgumentParser()
    parser.add_argument("html", help="Html file [REQUIRED]")
    parser.add_argument("excel", help="Excel file [REQUIRED]")

    args = parser.parse_args()
    compare(args.excel, args.html)


if __name__ == '__main__':
    main()
