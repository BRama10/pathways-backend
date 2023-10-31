# app.py
from __future__ import annotations
from flask import Flask, render_template, request
# from utils import Analysis, FairNode
import json
from flask_cors import CORS
from typing import Union, List, Dict, Any, Optional

import pandas as pd
import numpy as np
import ast

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
      self._build(list(map(str.strip,linked_codes)))

  def _build(self, codes: List[str]) -> None:
    for code in codes:
      if code == 'ISEF':
        self.linked.append(ISEFnode)
      else:
        _, row = [(i, r) for i, r in self.parent.df[self.parent.df['Fair Code'] == code].iterrows()][0]
        self.linked.append(FairNode(self.parent, row['Fair Name'], row['Fair Code'], linked_codes = row['Qualifies For']))


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
  def __init__(self, filepath: str ='full_data_exec_preds_1.csv') -> None:
    self.df = pd.read_csv(filepath)


    #temp jit file cleaning until file is fully preprocessed
    try:
      self.df.set_index('Unnamed: 0', inplace=True)
      self.df.index.name = None
    except:
      pass

    try:
      self.df['Qualifies For'] = self.df['Qualifies For'].apply(lambda ul : ul.split(',') if type(ul) == str else ul)
    except:
      pass

    try:
      self.df['Locations'] = self.df['Locations'].apply(lambda expr: ast.literal_eval(expr) if isinstance(expr, str) and expr.strip() and expr[0] in "[({s" and expr[-1] in ")}]" else expr)
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
    res = self.df[self.df['Fair Code'] == fair] if len(fair) in [5,6] else self.df[self.df['Fair Name'] == fair]

    if res.empty:
      return None
    #return {k : v.get(0) for k,v in res.to_dict().items()}
    return res

  def return_contacts(self, fairs: List[str]) -> Optional[List[Dict[str, str]]]:
    f = []

    for fair in fairs:
      row = self.df[self.df['Fair Code'] == fair] if len(fair) in [5,6] else self.df[self.df['Fair Name'] == fair]

      if row.empty:
        return None

      f.append({
          'name' : row['Fair Name'][0],
          'contact_person' : row['Contact Person'][0],
          'contact_email' : row['Contact Email'][0]
      })

    return f

  def return_fair_nodes(self, county: str, state: str, *args, **kwargs) -> Optional[List[FairNode]]:
    trees = []
    s_nodes = [FairNode(self, row['Fair Name'], row['Fair Code'], linked_codes = row['Qualifies For']) for index, row in self.df[self.df['Locations'].apply(lambda lst: any(sub in county for sub in lst)) & (self.df['State'] == state) & (self.df['Fair Type'] == 'Regional')].iterrows()]
    # print(s_nodes)
    for sn in s_nodes:
      sn.gen_tree(reset=True)
      trees.append(FairNode.get_tree(*args, **kwargs))
    return trees

  def fair_difficulty(self, fairs: Union[str, List[str]]) -> Optional[Union[float, List[float]]]:
    if isinstance(fairs, str):
      res = self.df[self.df['Fair Code'] == fairs] if len(fairs) in [5,6] else self.df[self.df['Fair Name'] == fairs]
    else:
      res = self.df[self.df['Fair Code'].isin(fairs)] if len(fairs) in [5,6] else self.df[self.df['Fair Name'].isin(fairs)]

    if res.empty:
      return None
    return res.loc[:,'scaled_diff_2014':]


app = Flask(__name__)
CORS(app)
a = Analysis()

def parse_auth():
    request.headers.get('your-header-name')

@app.route('/')
def index():
    return 'Hi!'

# @app.route('/finalists_fairs/<fair_name>/')
def getFinalistsByFair(fair_name):
    return json.dumps(int(eval(list(a.return_info(fair_name).to_dict().get('data_2023').values())[0])[2]))

def getDiffByFair(fair_name):
    return json.dumps(round(list(a.fair_difficulty(fair_name).to_dict().get('scaled_diff_2023').values())[0], 1))
# def getFinalistsByFair(fair_name):
#     return json.dumps(eval(list(a.return_info(fair_name).to_dict().get('data_2023').values())[0])[2])

@app.route('/get_fair_list/<county>/<state>/')
def getFairListByCountyAndState(county, state):
    target = None 

    for x in a.return_fair_nodes(county=county, state=state, pretty=False):
        try:
            if len(x[0]) == 3:
                target = x[0]
                break
            elif len(x[1]) == 3:
                target = x[1]
                break
        except:
            pass

    return_values = []

    if target:
        regional = a.return_info(target[0])

        return_values.append(
            {
                'name' : regional.at[regional.index[0], 'Fair Name'],
                'code' : regional.at[regional.index[0], 'Fair Code'],
                'contact_name' : regional.at[regional.index[0], 'Contact Person'],
                'email' : regional.at[regional.index[0], 'Contact Email'],
                'website' :regional.at[regional.index[0], 'Fair Link'],
            }
        )

        state = a.return_info(target[1])
        
        return_values.append(
            {
                'name' : state.at[state.index[0], 'Fair Name'],
                'code' : state.at[state.index[0], 'Fair Code'],
                'contact_name' : state.at[state.index[0], 'Contact Person'],
                'email' : state.at[state.index[0], 'Contact Email'],
                'website' :regional.at[regional.index[0], 'Fair Link'],
            }
        ) 
    
    return json.dumps({
        'fair_data' : return_values,
        'diff' : getDiffByFair(return_values[0]['code']),
        'num_finalists' : getFinalistsByFair(return_values[0]['code'])
    })
    



# if __name__ == '__main__':
#     app.run(host='0.0.0.0', debug=True, port="8080")
 