from pickle import FALSE
from flask import Flask, jsonify, render_template, redirect, request, url_for, session, flash, Response
from flask_mysqldb import MySQL, MySQLdb
from flask_mqtt import Mqtt
import cv2, imutils, os
import json
import numpy as np
from werkzeug.security import generate_password_hash, check_password_hash 

app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'sistema_salud'
app.secret_key = "super secret key dsdssadadsa"
app.config['MQTT_BROKER_URL'] = '192.168.68.103'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = None
app.config['MQTT_PASSWORD'] = None
app.config['MQTT_KEEPALIVE'] = 5
app.config['MQTT_TLS_ENABLED'] = False
app.config['MQTT_REFRESH_TIME'] = 1.0  # refresh time in seconds

mqtt = Mqtt(app)
mysql = MySQL(app)

#Variables de captura de video
global video 
video = cv2.VideoCapture(0,cv2.CAP_DSHOW)
#Variable para validar si el seguimiento de  rostro esta activado
global activado
activado = False
face_detector = cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")


# Un "middleware" que se ejecuta antes de responder a cualquier ruta. Aquí verificamos si el usuario ha iniciado sesión
@app.before_request
def antes_de_cada_peticion():
    ruta = request.path
    # Si no ha iniciado sesión y quiere ir a alguna ruta protegida, lo redireccionamos al login
    if not 'id_user' in session and ruta != "/login" and ruta != "/registro" and ruta != "/logout" and not ruta.startswith("/static"):
        return redirect("/login")
    # Bloquea ruta de login y registro si existe una sesion activa
    if  ruta == "/login" or ruta == "/registro":
      if 'id_user' in session:
          return redirect("/")
# Funciones de base de datos 
#Funcion insertar usuario 
def insertaUsuario(email, nombre, password):
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO tblusuarios (email, password,nombre)  VALUES (%s,%s,%s)",(email,password,nombre))
    mysql.connection.commit()
#Funcion obtener usuario 
def obtenUsuario(email):
     cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
     cur.execute("SELECT * FROM tblusuarios WHERE email=%s",(email,))
     mysql.connection.commit()
     results = cur.fetchone()
     return results
# Rutas
#Si hay login
@app.route('/get', methods = ["GET"])
def get():
    if 'id_user' in session:
        print(request.data)
        return 'si entra'
    else:
        return 'error'
# Ruta de Index
@app.route("/")
def index():
    video.release()
    return render_template('index.html')

#Ruta de registro 
@app.route("/registro",methods=["GET","POST"])
def registro():
    if request.method ==  'GET':
        error = 2
        return render_template('registro.html')
    else: 
            error = 2
            name = request.form['paciente']
            email = request.form['email']
            password = request.form['password']
            if not name:
                flash('Registra un nombre')
                error = 1
            if not email:
                flash('Registra un correo electronico')
                error = 1
            if not password:
                flash('Registra una clave de usuario')
                error = 1
            hash_password = generate_password_hash(password)
            resultado = obtenUsuario(email)
            if resultado:
                flash('La cuenta ya existe')
                error = 1
            else:
                if error == 2:
                    insertaUsuario(email,name,hash_password)
                    error = 0       
    return render_template('registro.html', error=error)

#Ruta de login
@app.route("/login",methods=["GET","POST"])
def login():
    if request.method ==  'GET':
        hayError = 0
        return render_template('login.html')
    if request.method == 'POST':
        hayError = 0
        email = request.form['email']
        password = request.form['password']
        resultado = obtenUsuario(email)
        if resultado: 
            if len(resultado) > 0 and check_password_hash(resultado['password'], password):
                session['id_user'] = resultado['iduser']
                session['nombre'] = resultado['nombre']
                session['email'] = resultado['email']
                x = {
                    "accion": "entra",
                    "usuario": resultado['iduser']}
                y = json.dumps(x)

                mqtt.publish('usuario/inicio', y)
                return redirect("/")
            else:
                hayError = 1
                error = "Los datos introducidos son incorrectos"
                return render_template('login.html', error=error, hayError=hayError)
        else:
            hayError = 1
            error = "Los datos introducidos son incorrectos"
            return render_template('login.html', error=error, hayError=hayError)
    else:
         hayError = 0
         return render_template('login.html', error=error, hayError=hayError)

# Ruta para cerrar sesión   
@app.route('/logout')
def logout():
    x = {
    "accion": "sale",
    "usuario": None}
    y = json.dumps(x)
    mqtt.publish('usuario/inicio', y)
    video.release()
    session.clear()
    return redirect('/')
# Funcion para validar si hay rostro asignado
def ValidaRostro(idUser):
    datosPath = 'D:/Users/fredd/Documents/Modular/Sistema de cuidado/Data'
    personaPath = datosPath + '/' +  str(idUser) + '/'
    if not os.path.exists(personaPath):
        existe = False
    else:
        existe= True
    return existe
# Ruta de videovigilancia
@app.route("/vigilancia",methods=["POST", "GET"])
def vigilancia(): 
    global video 
    global activado
    if ValidaRostro(session['id_user']):
        existe = 'si'
    else:
        existe = 'no'
    if request.method == 'POST':
        if request.form.get('Seguimiento') == 'facetrack':
            activado = not activado
            video.release()
            video = cv2.VideoCapture(0,cv2.CAP_DSHOW) 
            return render_template('vigilancia.html', activado=activado, existe=existe)
        if request.form.get('Movimiento'):
            video.release()
            video = cv2.VideoCapture(0,cv2.CAP_DSHOW) 
            if request.form.get('Movimiento') == "up":
                x = {"face": "no","move":"up"}
                y = json.dumps(x)
                mqtt.publish('usuario/camara', y)
            if request.form.get('Movimiento') == "down":
                x = {"face": "no","move":"down"}
                y = json.dumps(x)
                mqtt.publish('usuario/camara', y)
            if request.form.get('Movimiento') == "left":
                x = {"face": "no","move":"left"}
                y = json.dumps(x)
                mqtt.publish('usuario/camara', y)
            if request.form.get('Movimiento') == "right":
                x = {"face": "no","move":"right"}
                y = json.dumps(x)
                mqtt.publish('usuario/camara', y)
            return render_template('vigilancia.html', activado=activado, existe=existe)
    elif request.method == 'GET':
        video.release()
        video = cv2.VideoCapture(0,cv2.CAP_DSHOW) 
        return render_template('vigilancia.html', activado=activado, existe=existe)

#Ruta en la que se muestra video 
@app.route("/video_feed")
def video_feed():
     nombre = session['nombre']
     nombre = nombre[0:nombre.index(" ")]
     if activado: 
         face_recognizer = cv2.face.LBPHFaceRecognizer_create()
         face_recognizer.read('D:/Users/fredd/Documents/Modular/Sistema de cuidado/Trainer/'+str(session['id_user'])+'/modeloLBPHFace-'+str(session['id_user'])+'.xml')
     else:
         face_recognizer = ''
     return Response(deteccion(face_recognizer, nombre),
          mimetype = "multipart/x-mixed-replace; boundary=frame")
#Funcion para detectar el rostro 
def deteccion (facerec, nombre):
    faceXanterior = 0
    faceYanterior = 0
    while(video.isOpened()):
          ret, frame = video.read()
          frame = imutils.resize(frame, width=360)
          frame = cv2.flip(frame, 1)
          if(activado):
              if ret:
                  gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                  auxFrame = gray.copy()
                  faces = face_detector.detectMultiScale(gray, 1.3, 5)
                  for(x,y,w,h) in faces:
                    rostro = auxFrame[y:y+h,x:x+w]
                    rostro = cv2.resize(rostro,(150,150), interpolation=cv2.INTER_CUBIC)
                    result = facerec.predict(rostro)
                    if result[1] < 100:
                        cv2.putText(frame,'{}'.format(nombre),(x,y-25),2,1.1,(0,255,0),1,cv2.LINE_AA)
                        faceX = int(x + (w / 2.0))
                        faceY = int(y + (h / 2.0))
                        cv2.circle(frame, (faceX,faceY),5, (0,255,0))
                        if abs(faceX-faceXanterior) > 10 or abs(faceY-faceYanterior) > 10:
                            x = {"face": "si","x": faceX, "y":faceY}
                            y = json.dumps(x)
                            mqtt.publish('usuario/camara', y)
                        faceXanterior = faceX
                        faceYanterior = faceY 
                    (flag, encodedImage) = cv2.imencode(".jpg", frame)
                    if not flag:
                     continue
                    yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
                    bytearray(encodedImage) + b'\r\n')
          else:
            (flag, encodedImage) = cv2.imencode(".jpg", frame)
            if not flag:
                continue
            yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
                    bytearray(encodedImage) + b'\r\n')

#Ruta de perfil 
@app.route("/perfil", methods=["POST", "GET"])
def perfil():
    nombreFile = 'rostro-'+str(session['id_user']) + '.jpg'
    if ValidaRostro(session['id_user']):
        existe = 'si'
    else:
        existe = 'no'
    if request.method == 'POST':
         if request.form.get('Asignar rostro'):
             CapturarImagenes()
             return redirect(request.referrer)
         else:
             return render_template('perfil.html', existe=existe, nombreFile = nombreFile)      
    else:
         return render_template('perfil.html', existe=existe, nombreFile = nombreFile)
# Funcion de captura de imagenes
def CapturarImagenes():
    datosPath = 'D:/Users/fredd/Documents/Modular/Sistema de cuidado/Data'
    personaPath = datosPath + '/' +  str(session['id_user']) + '/'
    if not os.path.exists(personaPath):
        os.makedirs(personaPath)
    cap = cv2.VideoCapture(0,cv2.CAP_DSHOW)
    face_detector = cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
    count = 0
    while count < 200:
        ret, frame = cap.read()
        if ret == False: break
        frame = imutils.resize(frame, width=640)
        gray = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        auxFrame = frame.copy()
        faces = face_detector.detectMultiScale(gray, 1.3, 5)
        for(x,y,w,h) in faces:
            cv2.rectangle(frame,(x,y),(x+w,y+h), (0,255,0),2)
            rostro = auxFrame[y:y+h,x:x+w]
            rostro = cv2.resize(rostro,(150,150), interpolation=cv2.INTER_CUBIC)
            if count == 0:
                cv2.imwrite('D:/Users/fredd/Documents/Modular/Sistema de cuidado/static/'+'rostro-'+str(session['id_user'])+'.jpg',rostro)
            cv2.imwrite(personaPath+'rostro_{}.jpg'.format(count),rostro)
            count = count+1
        if count == 200:
            Entrenar(session['id_user'])
            break
    cap.release()
# Funcion entrenador 
def Entrenar(idUser):
    datosPath = 'D:/Users/fredd/Documents/Modular/Sistema de cuidado/Data/' + str(idUser)
    labels = []
    faceData = []
    label = 0
    for filename in os.listdir(datosPath):
        labels.append(label)
        faceData.append(cv2.imread(datosPath + '/' + filename,0)) 
    trainerPath = 'D:/Users/fredd/Documents/Modular/Sistema de cuidado/Trainer'
    personaTrainerPath = trainerPath + '/' +  str(session['id_user']) + '/'
    if not os.path.exists(personaTrainerPath):
        os.makedirs(personaTrainerPath)
    face_recognizer = cv2.face.LBPHFaceRecognizer_create()
    face_recognizer.train(faceData, np.array(labels))
    face_recognizer.write(personaTrainerPath + 'modeloLBPHFace-'+str(idUser) +'.xml')

if __name__=="__main__":
    app.run(debug=False)