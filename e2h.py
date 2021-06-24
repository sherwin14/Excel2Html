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

html_file_path = ""


def read_html(html_file):
    global html_file_path
    html_file_data = open(html_file, "r")
    # Reading the file
    html_file_path = os.path.realpath(html_file_data.name)

    index = html_file_data.read()
    soup = BeautifulSoup(index, 'html.parser')

    json_val = list()

    for tag in soup.find_all('a'):
        json_val.append(tag.attrs)

    return json_val


def compare(excel_file, html_file):
    excel_file_data = pd.read_excel(excel_file, sheet_name='FINAL', engine='openpyxl')
    pd.set_option('display.max_colwidth', 1000)

    excel_file_data['description'] = excel_file_data['Unnamed: 9'].str.replace("\"", "")
    excel_file_data['cat1'] = excel_file_data['Unnamed: 3'].str.replace("\"", "")
    excel_file_data['cat2'] = excel_file_data['Unnamed: 4'].str.replace("\"", "")
    excel_file_data.drop(columns=['Unnamed: 9', 'Unnamed: 3', 'Unnamed: 4'], inplace=True)

    pattern = r'(?:http)\S+(?:DI_EMAIL\s)\S+|(?:tel:|#|http|zet|tb)\S+'

    t_df = pd.DataFrame(excel_file_data, columns=['description', 'Unnamed: 12'])
    href = t_df['Unnamed: 12'].apply(lambda x: re.findall(pattern, x, re.IGNORECASE)).str
    excel_file_data['href'] = href[0]

    excel_df = pd.DataFrame(excel_file_data, columns=['description', 'cat1', 'cat2', 'href'])
    excel_df = excel_df.drop([0, 0])

    # html json to data frame
    j = json.loads(json.dumps(read_html(html_file)))
    html_df = pd.DataFrame(j, columns=['description', 'cat1', 'cat2', 'href'])

    html_df['from'] = "actual"
    excel_df['from'] = "expected"

    html_df = html_df[~html_df['href'].str.contains("Zeta")]
    html_df = html_df[~html_df['href'].str.contains("tbd")]
    html_df = html_df.drop_duplicates(keep="first")

    excel_df = excel_df[~excel_df['href'].str.contains("Zeta")]
    excel_df = excel_df[~excel_df['href'].str.contains("tbd")]

    df_result = pd.concat([excel_df, html_df]) \
        .drop_duplicates(['description', 'cat1', 'cat2', 'href'], keep=False)

    df_result = df_result.sort_values('description')

    df_result['result'] = np.where((df_result['description'].eq(df_result['description'].shift(-1)) &
                                    (df_result['cat1'].eq(df_result['cat1'].shift(-1))) &
                                    (df_result['cat2'].eq(df_result['cat2'].shift(-1))) &
                                    (df_result['href'].eq(df_result['href'].shift(-1)))), "True",
                                   np.where(df_result['from'].eq('expected'), "N/A", "False"))

    df_final = pd.DataFrame(df_result, columns=['description', 'cat1', 'cat2', 'href', 'from', 'result'])

    df_final = df_final.sort_values(['description'], ascending=[True])
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

    file = os.path.basename(html_file)
    filepath = Path(f'{os.getcwd()}/logs/{file.split(".")[0]}-{int(time.time())}.txt')
    filepath.parent.mkdir(parents=True, exist_ok=True)

    log_msg = f"\n============================================================================================\n" \
              f"{dt_string}\n"
    log_msg += f"Found {len(df_final[df_final['from'] == 'expected'])} " \
               f"discrepancies from {html_file_path}. Please see the output below.\n"
    log_msg += df_final.to_string(index=None)
    log_msg += "\n=============================================================================================\n"
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
