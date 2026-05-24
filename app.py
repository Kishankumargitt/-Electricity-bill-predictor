from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # For flash messages

# BESCOM domestic rates (approximate as of 2023; in ₹ per unit)
BESCOM_RATES = [
    (0, 50, 4.15),
    (51, 100, 5.60),
    (101, 200, 8.20),
    (201, float('inf'), 9.50)
]

# Function to calculate cost based on BESCOM slabs
def calculate_bescom_cost(kwh):
    cost = 0
    remaining_kwh = kwh
    for min_kwh, max_kwh, rate in BESCOM_RATES:
        if remaining_kwh > 0:
            slab_kwh = min(remaining_kwh, max_kwh - min_kwh + 1 if max_kwh != float('inf') else remaining_kwh)
            cost += slab_kwh * rate
            remaining_kwh -= slab_kwh
    return round(cost, 2)

# Pre-populated sample readings (dates, kWh, auto-calculated cost in ₹)
readings = [
    {'date': '2023-09-01', 'kwh': 45, 'cost': calculate_bescom_cost(45)},   # ~₹185.75
    {'date': '2023-09-08', 'kwh': 52, 'cost': calculate_bescom_cost(52)},   # ~₹232.20
    {'date': '2023-09-15', 'kwh': 60, 'cost': calculate_bescom_cost(60)},   # ~₹278.00
    {'date': '2023-09-22', 'kwh': 48, 'cost': calculate_bescom_cost(48)},   # ~₹198.40
    {'date': '2023-09-29', 'kwh': 70, 'cost': calculate_bescom_cost(70)},   # ~₹332.00
    {'date': '2023-10-06', 'kwh': 55, 'cost': calculate_bescom_cost(55)},   # ~₹250.75
    {'date': '2023-10-13', 'kwh': 80, 'cost': calculate_bescom_cost(80)},   # ~₹380.00
    {'date': '2023-10-20', 'kwh': 65, 'cost': calculate_bescom_cost(65)},   # ~₹304.75
]

@app.route('/')
def home():
    return render_template('index.html', bescom_rates=BESCOM_RATES)

@app.route('/add_reading', methods=['POST'])
def add_reading():
    try:
        date = request.form['date']
        kwh = float(request.form['kwh'])
        if kwh <= 0:
            flash('kWh must be a positive number.', 'error')
            return redirect(url_for('home'))
        # Auto-calculate cost using BESCOM rates
        auto_cost = calculate_bescom_cost(kwh)
        # Handle cost input: use provided value or default to auto_cost
        cost_input = request.form.get('cost', '').strip()
        if cost_input:
            cost = float(cost_input)
        else:
            cost = auto_cost
        if cost < 0:
            flash('Cost must be non-negative.', 'error')
            return redirect(url_for('home'))
        readings.append({'date': date, 'kwh': kwh, 'cost': cost})
        flash(f'Reading added! Cost used: ₹{cost:.2f} (auto-calculated if not provided).', 'success')
    except ValueError:
        flash('Invalid input. Please enter valid numbers for kWh and cost (if provided).', 'error')
    return redirect(url_for('home'))

@app.route('/history')
def history():
    return render_template('history.html', readings=readings)

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    prediction = None
    chart_url = None
    if request.method == 'POST':
        try:
            days = int(request.form['days'])
            if days <= 0:
                flash('Days must be a positive number.', 'error')
                return render_template('predict.html', prediction=prediction, chart_url=chart_url)
            if not readings:
                flash('No readings available for prediction.', 'error')
                return render_template('predict.html', prediction=prediction, chart_url=chart_url)
            
            df = pd.DataFrame(readings)
            model = LinearRegression()
            model.fit(df[['kwh']], df['cost'])
            avg_kwh = df['kwh'].mean()
            predicted_kwh = avg_kwh * (days / 30)
            prediction = model.predict([[predicted_kwh]])[0]
            
            # Generate chart
            plt.figure(figsize=(6, 4))
            plt.plot(df['date'], df['kwh'], marker='o', label='Historical kWh')
            plt.title('Electricity Usage Trend')
            plt.xlabel('Date')
            plt.ylabel('kWh')
            plt.xticks(rotation=45)
            plt.legend()
            img = io.BytesIO()
            plt.savefig(img, format='png')
            img.seek(0)
            chart_url = base64.b64encode(img.getvalue()).decode()
            plt.close()
        except Exception as e:
            flash(f'Error in prediction: {str(e)}', 'error')
    
    return render_template('predict.html', prediction=prediction, chart_url=chart_url)

if __name__ == '__main__':
    app.run(debug=True)