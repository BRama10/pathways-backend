# app.py
from __future__ import annotations
from flask import Flask, render_template, request, jsonify
# from utils import Analysis, FairNode
import json
from flask_cors import CORS
from typing import Union, List, Dict, Any, Optional

import pandas as pd
import numpy as np
import ast
from os.path import dirname, abspath, join
import pickle




dir = dirname(abspath(__file__))


class FairNode:
    tree_list = []

    @classmethod
    def get_tree(ctx, pretty: bool = True, delim: str = ' ===>>> ') -> List[str]:
        return [delim.join(branch) for branch in FairNode.tree_list] if pretty else [branch for branch in FairNode.tree_list]

    def __init__(self, parent: Optional[Analysis], name: str, code: str, linked: Optional[List[FairNode]] = None, linked_codes: Optional[List[str]] = None) -> None:
        self.name = name
        self.code = code
        self.linked = linked if linked is not None else []
        self.parent = parent

        if linked_codes:
            self._build(list(map(str.strip, linked_codes)))

    def _build(self, codes: List[str]) -> None:
        for code in codes:
            if code == 'ISEF':
                self.linked.append(ISEFnode)
            else:
                _, row = [
                    (i, r) for i, r in self.parent.df[self.parent.df['Fair Code'] == code].iterrows()][0]
                self.linked.append(FairNode(
                    self.parent, row['Fair Name'], row['Fair Code'], linked_codes=row['Qualifies For']))

    def gen_tree(self, path=None, reset=False) -> None:
        if reset:
            FairNode.tree_list = []

        if path is None:
            path = []

        if not self.linked:
            FairNode.tree_list.append(path + [self.name])
        else:
            for node in self.linked:
                node.gen_tree(path + [self.name])


ISEFnode = FairNode(None, 'ISEF', 'ISEF')


class Analysis:
    def __init__(self, filepath: str = dir+'/full_data_exec_preds_1.csv') -> None:
        self.df = pd.read_csv(filepath)

        # temp jit file cleaning until file is fully preprocessed
        try:
            self.df.set_index('Unnamed: 0', inplace=True)
            self.df.index.name = None
        except:
            pass

        try:
            self.df['Qualifies For'] = self.df['Qualifies For'].apply(
                lambda ul: ul.split(',') if type(ul) == str else ul)
        except:
            pass

        try:
            self.df['Locations'] = self.df['Locations'].apply(lambda expr: ast.literal_eval(expr) if isinstance(
                expr, str) and expr.strip() and expr[0] in "[({s" and expr[-1] in ")}]" else expr)
        except:
            pass
        # print(self.df['Locations'][2])
        # print(type(self.df['Locations'][2]))

    #   self.df = self.df.applymap(self._parse)

    # def _parse(self, expr):
    #   if isinstance(expr, str) and expr.strip() and expr[0] in "[({s" and expr[-1] in ")}]":
    #     return ast.literal_eval(expr)
    #   elif '.' in expr and (not '/' in expr) and (not '@' in expr):
    #     return float(expr)
    #   return expr

    def return_info(self, fair: str) -> Optional[Dict[str, Any]]:
        res = self.df[self.df['Fair Code'] == fair] if len(
            fair) in [5, 6, 7] else self.df[self.df['Fair Name'] == fair]

        if res.empty:
            return None
        # return {k : v.get(0) for k,v in res.to_dict().items()}
        return res

    def return_contacts(self, fairs: List[str]) -> Optional[List[Dict[str, str]]]:
        f = []

        for fair in fairs:
            row = self.df[self.df['Fair Code'] == fair] if len(
                fair) in [5, 6, 7] else self.df[self.df['Fair Name'] == fair]

            if row.empty:
                return None

            f.append({
                'name': row['Fair Name'][0],
                'contact_person': row['Contact Person'][0],
                'contact_email': row['Contact Email'][0]
            })

        return f

    def return_fair_nodes(self, county: str, state: str, *args, **kwargs) -> Optional[List[FairNode]]:
        trees = []
        s_nodes = [FairNode(self, row['Fair Name'], row['Fair Code'], linked_codes=row['Qualifies For']) for index, row in self.df[self.df['Locations'].apply(
            lambda lst: any(sub.split(' ')[0] in county for sub in lst)) & (self.df['State'] == state) & (self.df['Fair Type'] == 'Regional')].iterrows()]
        # print(s_nodes)
        for sn in s_nodes:
            sn.gen_tree(reset=True)
            trees.append(FairNode.get_tree(*args, **kwargs))
        return trees

    def fair_difficulty(self, fairs: Union[str, List[str]]) -> Optional[Union[float, List[float]]]:
        if isinstance(fairs, str):
            res = self.df[self.df['Fair Code'] == fairs] if len(
                fairs) in [5, 6, 7] else self.df[self.df['Fair Name'] == fairs]
        else:
            res = self.df[self.df['Fair Code'].isin(fairs)] if len(
                fairs) in [5, 6, 7] else self.df[self.df['Fair Name'].isin(fairs)]

        if res.empty:
            return None
        return res.loc[:, 'scaled_diff_2014':]


def get_category_counts(df, year, fairs):
    # Filter the DataFrame based on year and fair
    filtered_df = df[(df['year'] == year) & (df['fair'].isin(fairs))]

    # Count the occurrences of each category and convert to a dictionary
    category_counts = filtered_df['category'].value_counts().to_dict()

    # If a category is missing, add it to the dictionary with a count of 0
    all_categories = [
        'Earth and Environmental Sciences', 'Robotics and Intelligent Machines', 'Environmental Engineering',
        'Biochemistry', 'Systems Software', 'Embedded Systems',
        'Computational Biology and Bioinformatics',
        'Behavioral and Social Sciences', 'Biomedical Engineering',
        'Materials Science', 'Plant Sciences',
        'Biomedical and Health Sciences', 'Animal Sciences',
        'Engineering Technology: Statics & Dynamics', 'Chemistry',
        'Microbiology', 'Cellular and Molecular Biology',
        'Energy: Sustainable Materials and Design',
        'Translational Medical Science', 'Mathematics',
        'Physics and Astronomy', 'Engineering Mechanics',
        'Energy: Chemical', 'Energy: Physical', 'No Category'
    ]

    for category in all_categories:
        category_counts.setdefault(category, 0)

    return category_counts


df_isef = pd.read_csv(dir+'/isef_database_cleaned.csv')

# def isExisting(string):
#         try:
#             c, s = map(str.strip, string.split(','))
#             var = a.return_fair_nodes(c, s)
#             return bool(var)
#         except Exception as e:
#             # print(f"Error processing {string}: {str(e)}")
#             return False

a = Analysis()

# county_data, county_dict = pd.read_csv(dir+'/population_metric.csv'), {}
# county_data = list(filter(isExisting, county_data['Unnamed: 0'].unique()))
# print(county_data)

app = Flask(__name__)
CORS(app)




def parse_auth():
    request.headers.get('your-header-name')


@app.route('/')
def index():
    return 'Hi!'



# print(isExisting('Fairfax County, Virginia'))
# print(isExisting('Cow, Texas'))

@app.route('/get_county_names')
def getCountyList():
    # return json.dumps(list(county_data['Unnamed: 0'].unique()))

    # for item in list(county_data['Unnamed: 0'].unique()):
    # for item in county_data:
    #     county, state = item.split(", ")
    #     state = state.strip()

    #     if state not in county_dict:
    #         county_dict[state] = []

    #     county_dict[state].append(county)

    with open(f'{dir}/data.pkl', 'rb') as file:
        loaded_data = pickle.load(file)

    return json.dumps(loaded_data)
# @app.route('/finalists_fairs/<fair_name>/')


def getFinalistsByFair(fair_name):
    # print('cow')
    # print(a.return_info(fair_name).to_dict().get('data_2023'))
    return int(eval(list(a.return_info(fair_name).to_dict().get('data_2023').values())[0])[2])




def getDiffByFair(fair_name, pred=False):
    if pred:
        return round(list(a.fair_difficulty(fair_name).to_dict().get('scaled_diff_2024').values())[0], 1)
    return round(list(a.fair_difficulty(fair_name).to_dict().get('scaled_diff_2023').values())[0], 1)
# def getFinalistsByFair(fair_name):
#     return json.dumps(eval(list(a.return_info(fair_name).to_dict().get('data_2023').values())[0])[2])

def replace_nan(data):
    lst = []
    var = data[0]['fair_data']
    for v in range(len(var)):
      for k, i in var[v].items():
        print(i)
        if type(i) != list:
          if pd.isna(i):
            lst.append([v, k, i])
    print(lst)
    for l, m, n in lst:
      print(data[0]['fair_data'][l][m])
      data[0]['fair_data'][l][m] = "No Data"
      print(data[0]['fair_data'][l][m])
    return data



def replace_nan(value, replacement="No Data"):
    
    if isinstance(value, list):
        return [replace_nan(v) for v in value]
    elif isinstance(value, dict):
        return {k: replace_nan(v) for k, v in value.items()}
    elif pd.isna(value):
        return replacement
    else:
        return value
    
@app.route('/get_fair_list/<county>/<state>/')
def getFairListByCountyAndState(county: str, state: str):
    county, state = county.replace('+', ' '), state.replace('+', ' ')
    county, state = county.title(), state.title()
    target = None

    response_data = []

    for branch in a.return_fair_nodes(county=county, state=state, pretty=False)[0]:
        return_values = []
        regional = a.return_info(branch[0])

        cat_counts = get_category_counts(df_isef, 2023, [regional.at[regional.index[0], 'Fair Name']])

        return_values.append({
            'type': 'regional',
            'name': replace_nan(regional.at[regional.index[0], 'Fair Name']),
            'code': replace_nan(regional.at[regional.index[0], 'Fair Code']),
            'contact_name': replace_nan(regional.at[regional.index[0], 'Contact Person']),
            'email': replace_nan(regional.at[regional.index[0], 'Contact Email']),
            'website': replace_nan(regional.at[regional.index[0], 'Fair Link']),
            'num_finalists': getFinalistsByFair(regional.at[regional.index[0], 'Fair Code']),
            'diff': getDiffByFair(regional.at[regional.index[0], 'Fair Code']),
            'pred_diff': getDiffByFair(regional.at[regional.index[0], 'Fair Code'], pred=True),
            'sectors': replace_nan(list(cat_counts.keys())),
            'breakdown': replace_nan(list(cat_counts.values()))
        })

        if len(branch) == 3:
            state = a.return_info(branch[1])

            cat_counts = get_category_counts(df_isef, 2023, [state.at[state.index[0], 'Fair Name']])

            return_values.append({
                'type': 'state',
                'name': replace_nan(state.at[state.index[0], 'Fair Name']),
                'code': replace_nan(state.at[state.index[0], 'Fair Code']),
                'contact_name': replace_nan(state.at[state.index[0], 'Contact Person']),
                'email': replace_nan(state.at[state.index[0], 'Contact Email']),
                'website': replace_nan(state.at[state.index[0], 'Fair Link']),
                'num_finalists': getFinalistsByFair(state.at[state.index[0], 'Fair Code']),
                'diff': getDiffByFair(state.at[state.index[0], 'Fair Code']),
                'pred_diff': getDiffByFair(state.at[state.index[0], 'Fair Code'], pred=True),
                'sectors': replace_nan(list(cat_counts.keys())),
                'breakdown': replace_nan(list(cat_counts.values()))
            })

            state_codes = [r.get(1) for i, r in a.df[a.df['State'] == regional.at[regional.index[0], 'State']].iterrows()]
            cat_counts = get_category_counts(df_isef, 2023, [r.get(3) for i, r in a.df[a.df['State'] == regional.at[regional.index[0], 'State']].iterrows()])

            response_data.append({
                'fair_data': replace_nan(return_values),
                'overall_finalists': sum([getFinalistsByFair(sc) for sc in state_codes]),
                'overall_diff': round(np.mean([getDiffByFair(sc) for sc in state_codes]), 1),
                'overall_pred_diff': round(np.mean([getDiffByFair(sc, pred=True) for sc in state_codes]), 1),
                'overall_sectors': replace_nan(list(cat_counts.keys())),
                'overall_breakdown': replace_nan(list(cat_counts.values())),
            })
        else:
            response_data.append({
                'fair_data': replace_nan(return_values),
                'overall_finalists': replace_nan(return_values[0]['num_finalists']),
                'overall_diff': replace_nan(return_values[0]['diff']),
                'overall_pred_diff': replace_nan(return_values[0]['pred_diff']),
                'overall_sectors': replace_nan(return_values[0]['sectors']),
                'overall_breakdown': replace_nan(return_values[0]['breakdown']),
            })

    return json.dumps(replace_nan(response_data))

# def getFairListByCountyAndState(county: str, state: str):
#     county, state = county.replace('+', ' '), state.replace('+', ' ')
#     county, state = county.title(), state.title()
#     target = None

#     response_data =[]
#     # print(a.return_fair_nodes(county=county, state=state))

#     for branch in a.return_fair_nodes(county=county, state=state, pretty=False)[0]:
#         return_values = []
#         regional = a.return_info(branch[0])

#         cat_counts = get_category_counts(df_isef, 2023, [regional.at[regional.index[0], 'Fair Name']])

#         return_values.append(
#             {
#                 'type': 'regional',
#                 'name': regional.at[regional.index[0], 'Fair Name'],
#                 'code': regional.at[regional.index[0], 'Fair Code'],
#                 'contact_name': regional.at[regional.index[0], 'Contact Person'],
#                 'email': regional.at[regional.index[0], 'Contact Email'],
#                 'website': regional.at[regional.index[0], 'Fair Link'],
#                 'num_finalists': getFinalistsByFair(regional.at[regional.index[0], 'Fair Code']),
#                 'diff': getDiffByFair(regional.at[regional.index[0], 'Fair Code']),
#                 'pred_diff': getDiffByFair(regional.at[regional.index[0], 'Fair Code'], pred=True),
#                 'sectors' : list(cat_counts.keys()),
#                 'breakdown' : list(cat_counts.values())
#             }
#         )

#         if len(branch) == 3:
#             #regional, state, isef
#             state = a.return_info(branch[1])

#             cat_counts = get_category_counts(df_isef, 2023, [state.at[state.index[0], 'Fair Name']])

#             return_values.append(
#                 {
#                     'type': 'state',
#                     'name': state.at[state.index[0], 'Fair Name'],
#                     'code': state.at[state.index[0], 'Fair Code'],
#                     'contact_name': state.at[state.index[0], 'Contact Person'],
#                     'email': state.at[state.index[0], 'Contact Email'],
#                     'website': regional.at[regional.index[0], 'Fair Link'],
#                     'num_finalists': getFinalistsByFair(state.at[state.index[0], 'Fair Code']),
#                     'diff': getDiffByFair(state.at[state.index[0], 'Fair Code']),
#                     'pred_diff': getDiffByFair(state.at[state.index[0], 'Fair Code'], pred=True),
#                     'sectors' : list(cat_counts.keys()),
#                     'breakdown' : list(cat_counts.values())
#                 }
#             )

    
#             state_codes = [r.get(1) for i, r in a.df[a.df['State'] == regional.at[regional.index[0], 'State']].iterrows()]
#             cat_counts = get_category_counts(df_isef, 2023,[r.get(3) for i, r in a.df[a.df['State'] == regional.at[regional.index[0], 'State']].iterrows()])
            
#             response_data.append({
#                 'fair_data' : return_values,
#                 'overall_finalists' : sum([getFinalistsByFair(sc) for sc in state_codes]),
#                 'overall_diff' : round(np.mean([getDiffByFair(sc) for sc in state_codes]),1),
#                 'overall_pred_diff' : round(np.mean([getDiffByFair(sc, pred=True) for sc in state_codes]),1),
#                 'overall_sectors' : list(cat_counts.keys()),
#                 'overall_breakdown' : list(cat_counts.values()),
#             })
#         else:
#             response_data.append({
#                 'fair_data' : return_values,
#                 'overall_finalists' : return_values[0]['num_finalists'],
#                 'overall_diff' : return_values[0]['diff'],
#                 'overall_pred_diff' : return_values[0]['pred_diff'],
#                 'overall_sectors' : return_values[0]['sectors'],
#                 'overall_breakdown' : return_values[0]['breakdown'],
#             })
    
#     return json.dumps(replace_nan(response_data))


    # for x in a.return_fair_nodes(county=county, state=state, pretty=False):
    #     try:
    #         if len(x[0]) == 3:
    #             target = x[0]
    #             break
    #         elif len(x[1]) == 3:
    #             target = x[1]
    #             break
    #     except:
    #         pass

    # return_values = []

    # if target:
    #     regional = a.return_info(target[0])

        # return_values.append(
        #     {
        #         'name': regional.at[regional.index[0], 'Fair Name'],
        #         'code': regional.at[regional.index[0], 'Fair Code'],
        #         'contact_name': regional.at[regional.index[0], 'Contact Person'],
        #         'email': regional.at[regional.index[0], 'Contact Email'],
        #         'website': regional.at[regional.index[0], 'Fair Link'],
        #     }
        # )

        # state = a.return_info(target[1])

        # return_values.append(
        #     {
        #         'name': state.at[state.index[0], 'Fair Name'],
        #         'code': state.at[state.index[0], 'Fair Code'],
        #         'contact_name': state.at[state.index[0], 'Contact Person'],
        #         'email': state.at[state.index[0], 'Contact Email'],
        #         'website': regional.at[regional.index[0], 'Fair Link'],
        #     }
        # )

    #     cat_counts = get_category_counts(df_isef, 2023, return_values[0]['name'])

    #     for item in return_values:
    #         for key, value in item.items():
    #             if not isinstance(value, str):
    #                 item[key] = 'N/A'

    #     return json.dumps({
    #         'fair_data': return_values,
    #         'diff': getDiffByFair(return_values[0]['code']),
    #         'num_finalists': getFinalistsByFair(return_values[0]['code']),
    #         'sectors' : list(cat_counts.keys()),
    #         'breakdown' : list(cat_counts.values())
    #     })
    # else:
    #     return json.dumps(0)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port="8080")
