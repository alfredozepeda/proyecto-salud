from flask import Flask, jsonify, render_template, redirect, request, url_for, session, flash, Response
from flask_mysqldb import MySQL, MySQLdb
import cv2 
from werkzeug.security import generate_password_hash, check_password_hash 

app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'sistema_salud'
app.secret_key = "super secret key dsdssadadsa"
mysql = MySQL(app)

#Variables de captura de video
global video 
video = cv2.VideoCapture(0,cv2.CAP_DSHOW)
#Variable para validar si el seguimiento de  rostro esta activado
global activado
activado = True
face_detector = cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")

# Un "middleware" que se ejecuta antes de responder a cualquier ruta. Aquí verificamos si el usuario ha iniciado sesión
@app.before_request
def antes_de_cada_peticion():
    ruta = request.path
    # Si no ha iniciado sesión y quiere ir a alguna ruta protegida, lo redireccionamos al login
    if not 'id_user' in session and ruta != "/login" and ruta != "/registro" and ruta != "/logout" and not ruta.startswith("/static"):
        return redirect("/login")
    if  ruta == "/login" or ruta == "/registro":
      if 'id_user' in session:
          return redirect("/")
#Funcion para detectar el rostro 
def deteccion ():
    while(video.isOpened()):
          ret, frame = video.read()
          if(activado):
              if ret:
                  gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                  faces = face_detector.detectMultiScale(gray, 1.3, 5)
                  for (x, y, w, h) in faces:
                   faceX = int(x + (w / 2.0))
                   faceY = int(y + (h / 2.0))
                   cv2.circle(frame, (faceX,faceY),5, (0,255,0))
                   print(str(faceX) + "-" + str(faceY))
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

#Ruta en la que se muestra video 
@app.route("/video_feed")
def video_feed():
     return Response(deteccion(),
          mimetype = "multipart/x-mixed-replace; boundary=frame")

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


# Ruta para cerrar sesión   
@app.route('/logout')
def logout():
    video.release()
    session.clear()
    return redirect('/')

# Ruta de videovigilancia
@app.route("/vigilancia",methods=["POST", "GET"])
def vigilancia(): 
    global video 
    global activado
    if request.method == 'POST':
        if request.form.get('Seguimiento') == 'facetrack':
            activado = not activado
            video.release()
            video = cv2.VideoCapture(0,cv2.CAP_DSHOW) 
            return render_template('vigilancia.html', activado=activado)
        if request.form.get('Movimiento'):
            video.release()
            video = cv2.VideoCapture(0,cv2.CAP_DSHOW) 
            if request.form.get('Movimiento') == "up":
                print("Mover arriba")
            if request.form.get('Movimiento') == "down":
                print("Mover abajo")
            if request.form.get('Movimiento') == "left":
                print("Mover izquierda")
            if request.form.get('Movimiento') == "right":
                print("Mover derecha")
            return render_template('vigilancia.html', activado=activado)
    else:
        video = cv2.VideoCapture(0,cv2.CAP_DSHOW)
        return render_template('vigilancia.html', activado=activado)

# Ruta de registro 
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

#Rutta de index
@app.route("/")
def index():
    video.release()
    return render_template('index.html')

# Ruta de login
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

if __name__=="__main__":
    app.run(debug=False)

    