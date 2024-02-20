from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit
import pyodbc
import pandas as pd
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app)

def get_db_connection():
    conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=HospitalDB;Trusted_Connection=yes')
    cursor = conn.cursor()
    cursor.execute("SELECT 1;")
    print("Database connection verified:", cursor.fetchone())
    return conn, cursor

@app.route('/')
def index():
    return render_template('index.html.html')

@app.route('/ingresar', methods=['GET', 'POST'])
def ingresar():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        cuarto = request.form.get('cuarto')
        camilla = request.form.get('camilla')
        especialidad = request.form.get('especialidad')
        conn, cursor = get_db_connection()
        id = None
        try:
            cursor.execute("INSERT INTO dbo.Pacientes (Nombre, Cuarto, Camilla, Especialidad) OUTPUT INSERTED.ID VALUES (?, ?, ?, ?)", (nombre, cuarto, camilla, especialidad))
            id = cursor.fetchone()[0]
            conn.commit()
            print("Datos insertados en la base de datos:", id, nombre, cuarto, camilla, especialidad)
        except pyodbc.Error as ex:
            print("Ocurrió un error al intentar insertar los datos:", ex)
        finally:
            conn.close()
        if id is not None:
            data = {'ID': id, 'Nombre': nombre, 'Cuarto': cuarto, 'Camilla': camilla, 'Especialidad': especialidad}
            socketio.emit('update data', data)
            print("Datos enviados a través de Socket.IO:", data)

            # Añade la fecha actual a los datos
            data['Fecha'] = datetime.now()

            # Carga los datos existentes del archivo de Excel
            try:
                df = pd.read_excel('datos.xlsx')
            except FileNotFoundError:
                df = pd.DataFrame()

            # Añade los nuevos datos al final del DataFrame
            df = pd.concat([df, pd.DataFrame([data])])

            # Guarda los datos en el archivo de Excel
            df.to_excel('datos.xlsx', index=False)
        return redirect(url_for('index'))
    return render_template('ingresar.html')

@socketio.on('delete data')
def handle_delete(data_id):
    conn, cursor = get_db_connection()
    try:
        cursor.execute("DELETE FROM dbo.Pacientes WHERE ID = ?", (data_id,))
        conn.commit()
        print("Datos borrados de la base de datos:", data_id)
    except pyodbc.Error as ex:
        print("Ocurrió un error al intentar borrar los datos:", ex)
    finally:
        conn.close()

    # Emitir un evento de Socket.IO a todos los clientes para informarles de la eliminación
    socketio.emit('delete data', data_id)

if __name__ == '__main__':
    socketio.run(app)
