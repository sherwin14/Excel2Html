# coding=utf-8
import argparse
import os
import time
import numpy as np
import pandas as pd
import json
from bs4 import BeautifulSoup
from datetime import datetime

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
    # return [x for x in j if x['description'] == description]


def compare(excel_file, html_file):
    excel_file_data = pd.read_excel(excel_file, sheet_name='FINAL', engine='openpyxl')
    pd.set_option('display.max_colwidth', 1000)

    excel_file_data['description'] = excel_file_data['Unnamed: 9'].str.replace("\"", "")
    excel_file_data['cat1'] = excel_file_data['Unnamed: 3'].str.replace("\"", "")
    excel_file_data['cat2'] = excel_file_data['Unnamed: 4'].str.replace("\"", "")
    excel_file_data.drop(columns=['Unnamed: 9', 'Unnamed: 3', 'Unnamed: 4'], inplace=True)

    if 'Unnamed: 12' in excel_file_data.head():
        new_href = excel_file_data['Unnamed: 12'].str.split(r"\" ", expand=True)

        excel_file_data['href'] = new_href[3]
        excel_file_data.drop(columns='Unnamed: 12', inplace=True)

    excel_df = pd.DataFrame(excel_file_data, columns=['description', 'cat1', 'cat2', 'href']) \
        .rename(
        columns={'Unnamed: 9': 'description', 'Unnamed: 3': 'cat1', 'Unnamed: 4': 'cat2', 'Unnamed: 12': 'href'})

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

    df_result = pd.concat([excel_df, html_df]).drop_duplicates(['description', 'cat1', 'cat2', 'href'], keep=False)

    df_result = df_result.sort_values('description')
    df_result['result'] = np.where((df_result['description'].eq(df_result['description'].shift(-1)) &
                                    (df_result['cat1'].eq(df_result['cat1'].shift(-1))) &
                                    (df_result['cat2'].eq(df_result['cat2'].shift(-1))) &
                                    (df_result['href'].eq(df_result['href'].shift(-1)))), "True",
                                   np.where(df_result['from'].eq('expected'), "N/A", "False"))

    df_final = pd.DataFrame(df_result, columns=['description', 'href', 'cat1', 'cat2', 'from', 'result'])
    data_msg = ""

    for idx, rows in df_final.iterrows():
        if rows['result'] == 'False':
            data_msg += f"\n{rows['description']}\t{rows['href']}\t{rows['cat1']}" \
                        f"\t{rows['cat2']}\t{rows['from']}\t\t{rows['result']}\n"

        else:
            data_msg += f"\n{rows['description']}\t{rows['href']}\t{rows['cat1']}" \
                        f"\t{rows['cat2']}\t{rows['from']}\t\t{rows['result']}"

            # datetime object containing current date and time

    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    filename = f'{html_file.split(".")[0]}-{int(time.time())}.txt'
    log_msg = f"\n=================================================================================\n{dt_string}\n"
    log_msg += f"Found {len(df_final[df_final['from'] == 'expected'])} " \
               f"discrepancies from {html_file_path}. Please see the output below.\n"
    log_msg += data_msg
    log_msg += "\n=================================================================================\n"
    print(log_msg)

    output_file = open(filename, 'a')
    output_file.write(log_msg)
    output_file.close()
    print(f"Successfully created log file in {filename}")


def main():
    global html_file_path
    parser = argparse.ArgumentParser()
    parser.add_argument("html", help="Html file [REQUIRED]")
    parser.add_argument("excel", help="Excel file [REQUIRED]")

    args = parser.parse_args()
    compare(args.excel, args.html)


if __name__ == '__main__':
    main()
