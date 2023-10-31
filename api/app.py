# app.py
from flask import Flask, render_template, request
from utils import Analysis, FairNode
import json
from flask_cors import CORS

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
 