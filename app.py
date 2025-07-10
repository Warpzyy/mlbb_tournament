from flask import Flask, render_template, request, redirect, url_for, flash
from flask import session
import os
import sqlite3

app = Flask(__name__)
app.secret_key = 'rahasia'


#index
@app.route('/')
def index():
    conn = get_db_connection()

    # Ambil jadwal
    tim_list = conn.execute('SELECT nama_tim FROM tim').fetchall()
    tim_nama = [tim['nama_tim'] for tim in tim_list]
    jadwal_pertandingan = []
    for i in range(len(tim_nama)):
        for j in range(i + 1, len(tim_nama)):
            jadwal_pertandingan.append((tim_nama[i], tim_nama[j]))

    # Ambil hasil
    hasil_list = conn.execute('SELECT * FROM hasil ORDER BY id DESC').fetchall()
    conn.close()

    return render_template('index.html', jadwal=jadwal_pertandingan, hasil=hasil_list)



def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()

    # Buat tabel tim
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tim (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_tim TEXT NOT NULL,
            anggota TEXT NOT NULL,
            kontak TEXT NOT NULL
        )
    ''')

    # Buat tabel hasil
    conn.execute('''
        CREATE TABLE IF NOT EXISTS hasil (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tim1 TEXT NOT NULL,
            tim2 TEXT NOT NULL,
            skor1 INTEGER NOT NULL,
            skor2 INTEGER NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


#daftar
@app.route('/daftar', methods=['GET', 'POST'])
def daftar():
    if request.method == 'POST':
        nama_tim = request.form['nama_tim']
        anggota = request.form['anggota']
        kontak = request.form['kontak']

        conn = get_db_connection()
        conn.execute('INSERT INTO tim (nama_tim, anggota, kontak) VALUES (?, ?, ?)',
                     (nama_tim, anggota, kontak))
        conn.commit()
        conn.close()

        flash('Tim berhasil didaftarkan!', 'success')
        return redirect(url_for('daftar'))

    # Ambil semua data tim dari database
    conn = get_db_connection()
    daftar_tim = conn.execute('SELECT * FROM tim').fetchall()
    conn.close()

    return render_template('daftar.html', daftar_tim=daftar_tim)


@app.route('/jadwal')
def jadwal():
    
    # Ambil semua tim dari database
    conn = get_db_connection()
    tim_list = conn.execute('SELECT nama_tim FROM tim').fetchall()
    conn.close()

    # Convert hasil ke list nama tim
    tim_nama = [tim['nama_tim'] for tim in tim_list]

    # Generate round-robin match (setiap tim bertemu semua tim lainnya 1x)
    jadwal_pertandingan = []
    for i in range(len(tim_nama)):
        for j in range(i + 1, len(tim_nama)):
            jadwal_pertandingan.append((tim_nama[i], tim_nama[j]))

    return render_template('jadwal.html', jadwal=jadwal_pertandingan)




#hasil
@app.route('/hasil', methods=['GET', 'POST'])
def hasil():
    if not session.get('admin'):
        flash("Silakan login terlebih dahulu.", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    tim_list = conn.execute('SELECT nama_tim FROM tim').fetchall()

    if not tim_list:
        flash("Belum ada tim yang terdaftar. Silakan daftar tim dulu.", "warning")
        return redirect(url_for('daftar'))

    if request.method == 'POST':
        tim1 = request.form['tim1']
        skor1 = int(request.form['skor1'])
        tim2 = request.form['tim2']
        skor2 = int(request.form['skor2'])

        if tim1 == tim2:
            flash("Tim tidak boleh melawan dirinya sendiri!", "danger")
            return redirect(url_for('hasil'))

        conn.execute('INSERT INTO hasil (tim1, tim2, skor1, skor2) VALUES (?, ?, ?, ?)',
                     (tim1, tim2, skor1, skor2))
        conn.commit()
        flash("Hasil pertandingan berhasil disimpan!", "success")
        return redirect(url_for('hasil'))

    hasil_list = conn.execute('SELECT * FROM hasil').fetchall()
    conn.close()
    return render_template('hasil.html', tim_list=tim_list, hasil=hasil_list)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Admin login hardcoded
        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            flash('Login berhasil!', 'success')
            return redirect(url_for('hasil'))
        else:
            flash('Username atau password salah.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

#logout
@app.route('/logout')
def logout():
    session.pop('admin', None)
    flash('Berhasil logout.', 'info')
    return redirect(url_for('login'))

#dashboard
@app.route('/dashboard')
def dashboard():
    if not session.get('admin'):
        flash("Silakan login sebagai admin terlebih dahulu.", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()

    # Hitung jumlah tim
    total_tim = conn.execute('SELECT COUNT(*) FROM tim').fetchone()[0]

    # Hitung jumlah pertandingan
    total_pertandingan = conn.execute('SELECT COUNT(*) FROM hasil').fetchone()[0]

    # (Opsional) Hitung tim dengan kemenangan terbanyak
    top_tim = conn.execute('''
        SELECT tim1 AS nama, COUNT(*) as menang FROM hasil
        WHERE skor1 > skor2
        GROUP BY tim1
        UNION ALL
        SELECT tim2 AS nama, COUNT(*) as menang FROM hasil
        WHERE skor2 > skor1
        GROUP BY tim2
    ''').fetchall()

    # Gabung & hitung total kemenangan
    kemenangan = {}
    for row in top_tim:
        nama = row['nama']
        menang = row['menang']
        kemenangan[nama] = kemenangan.get(nama, 0) + menang

    # Urutkan dari yang terbanyak
    top_list = sorted(kemenangan.items(), key=lambda x: x[1], reverse=True)

    conn.close()

    return render_template('dashboard.html',
                           total_tim=total_tim,
                           total_pertandingan=total_pertandingan,
                           top_list=top_list)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

