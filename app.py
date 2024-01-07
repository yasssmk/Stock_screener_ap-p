from flask import Flask, request, jsonify
import utils.Stock_selection  # Import your backend function

app = Flask(__name__)

@app.route('/add_stock', methods=['POST'])
def add_stock():
    symbol = request.json.get('symbol').upper()
    response = utils.Stock_selection.add_manually_selection(symbol)
    return jsonify(message=response)

if __name__ == '__main__':
    app.run(debug=True)

