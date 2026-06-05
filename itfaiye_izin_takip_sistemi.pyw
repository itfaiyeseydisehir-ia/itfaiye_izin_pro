import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import calendar
from datetime import datetime, timedelta, date
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import threading
import customtkinter as ctk
import ctypes

ctk.set_appearance_mode("Light") 
ctk.set_default_color_theme("blue")

# Eğer tkcalendar kütüphanesi yüklü değilse hata vermemesi için kontrol
try:
    from tkcalendar import DateEntry
except ImportError:
    messagebox.showerror("Hata", "Lütfen terminale 'pip install tkcalendar' yazarak takvim bileşenini yükleyin.")

# --- AYARLAR VE SABİTLER ---
VARDİYA_RENKLERİ = {1: "#C62828", 2: "#F9A825", 3: "#1565C0", "Gündüz": "#78909C"} 
SU_AN_YIL = datetime.now().year 
REF_DATE = date(2026, 3, 1) 
REF_VARDİYA = 2

# RESMİ TATİLLER
TATIL_ADLARI = {
    "01/01": "Yılbaşı", "23/04": "Ulusal Egemenlik ve Çocuk Bayramı",
    "01/05": "Emek ve Dayanışma Günü", "19/05": "Atatürk'ü Anma, Gençlik ve Spor Bayramı",
    "15/07": "Demokrasi ve Milli Birlik Günü", "30/08": "Zafer Bayramı", "29/10": "Cumhuriyet Bayramı"
}
RESMI_TATILLER = list(TATIL_ADLARI.keys())

# DİNİ BAYRAMLAR (Kodun içindeki sabit liste)
DINI_TATIL_DETAY = {
    "19/03/2026": "Ramazan Bayramı (Arefe)", "20/03/2026": "Ramazan Bayramı (1. Gün)",
    "21/03/2026": "Ramazan Bayramı (2. Gün)", "22/03/2026": "Ramazan Bayramı (3. Gün)",
    "26/05/2026": "Kurban Bayramı (Arefe)", "27/05/2026": "Kurban Bayramı (1. Gün)",
    "28/05/2026": "Kurban Bayramı (2. Gün)", "29/05/2026": "Kurban Bayramı (3. Gün)", "30/05/2026": "Kurban Bayramı (4. Gün)"
}

LBL_FONT = ("Segoe UI", 10, "bold")
ENT_FONT = ("Segoe UI", 11)
COLORS = {"arsiv": "#4A148C", "devir": "#E65100", "rapor": "#263238", "excel": "#1B5E20", "sil": "#B71C1C", "mavi": "#0D47A1", "koyu_mavi": "#1A237E", "mazeret": "#00796B"}

def pencere_ortala(pencere, g, y):
    ekran_g = pencere.winfo_screenwidth()
    ekran_y = pencere.winfo_screenheight()
    
    # Eğer girilen değer ekran boyutundan büyükse ekranın %90'ını kapla
    if g > ekran_g: g = int(ekran_g * 0.9)
    if y > ekran_y: y = int(ekran_y * 0.9)
    
    x = (ekran_g // 2) - (g // 2)
    y_konum = (ekran_y // 2) - (y // 2)
    pencere.geometry(f"{g}x{y}+{x}+{y_konum}")

def vardiya_bul(tarih, vardiya_tipi="1"):
    if vardiya_tipi == "Gündüz": return "Gündüz"
    if isinstance(tarih, datetime): tarih = tarih.date()
    delta = (tarih - REF_DATE).days
    return ((delta + (REF_VARDİYA - 1)) % 3) + 1

def veritabani_kur():
    conn = sqlite3.connect("itfaiye_izin.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS personel (id INTEGER PRIMARY KEY AUTOINCREMENT, sicil_no TEXT, isim TEXT, statu TEXT, vardiya TEXT, toplam_hak INTEGER, hakedis_tarihi TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS izinler (id INTEGER PRIMARY KEY AUTOINCREMENT, personel_id INTEGER, baslangic TEXT, bitis TEXT, harcanan_gun INTEGER, yil INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS devir_izinler (id INTEGER PRIMARY KEY AUTOINCREMENT, personel_id INTEGER, yil INTEGER, kalan_gun INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS raporlar (id INTEGER PRIMARY KEY AUTOINCREMENT, personel_id INTEGER, baslangic TEXT, bitis TEXT, gun_sayisi INTEGER, aciklama TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS mazeret_izinleri (id INTEGER PRIMARY KEY AUTOINCREMENT, personel_id INTEGER, baslangic TEXT, bitis TEXT, gun_sayisi INTEGER, aciklama TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS hakedis_takip (id INTEGER PRIMARY KEY AUTOINCREMENT, personel_id INTEGER, yil INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS izin_detaylari (id INTEGER PRIMARY KEY AUTOINCREMENT, izin_id INTEGER, devir_id INTEGER, miktar INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS manuel_bayramlar (id INTEGER PRIMARY KEY AUTOINCREMENT, ad TEXT, tarih TEXT)''')
    conn.commit(); conn.close()

class OzelTakvim(tk.Frame):
    def __init__(self, master, callback):
        super().__init__(master, bg="white", highlightbackground="#455A64", highlightthickness=2)
        self.callback = callback
        self.simdiki_yil = datetime.now().year
        self.simdiki_ay = datetime.now().month
        self.secili_tarih = None
        ctrl = tk.Frame(self, bg="#455A64")
        ctrl.pack(fill="x")
        tk.Button(ctrl, text=" < ", command=self.ay_geri, font=("Arial", 12, "bold"), fg="white", bg="#455A64", bd=0).pack(side="left", padx=10)
        self.lbl_ay = tk.Label(ctrl, text="", font=("Segoe UI", 13, "bold"), bg="#455A64", fg="white", width=15); self.lbl_ay.pack(side="left", pady=5)
        tk.Button(ctrl, text=" > ", command=self.ay_ileri, font=("Arial", 12, "bold"), fg="white", bg="#455A64", bd=0).pack(side="right", padx=10)
        
        # BÜYÜTÜLMÜŞ CANVAS BOYUTU
        self.canvas = tk.Canvas(self, width=520, height=430, bg="white", highlightthickness=0)
        self.canvas.pack(pady=5, padx=5)
        self.canvas.bind("<Button-1>", self.tiklama); self.ciz()

    def ciz(self):
        self.canvas.delete("all")
        ay_adi = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        self.lbl_ay.config(text=f"{ay_adi[self.simdiki_ay]} {self.simdiki_yil}")
        
        # GÜN İSİMLERİ HİZALAMASI (Pz, Sa... kaybolmaması için çarpanı 58'den 70'e çıkardık)
        gunler = ["Pz", "Sa", "Ça", "Pe", "Cu", "Ct", "Pa"]
        for i, g in enumerate(gunler): 
            # 45 + i*70 yaparak gün isimlerini kutuların tam ortasına hizaladık
            self.canvas.create_text(45 + i*70, 20, text=g, font=("Segoe UI", 12, "bold"), fill="#333")
        
        cal = calendar.monthcalendar(self.simdiki_yil, self.simdiki_ay)
        for r, hafta in enumerate(cal):
            for c, gun in enumerate(hafta):
                if gun == 0: continue
                
                # KUTU KOORDİNATLARI (Genişlik çarpanı: 70, Yükseklik çarpanı: 65)
                x1, y1 = 10 + c*70, 45 + r*65 
                x2, y2 = x1 + 68, y1 + 60 # Kutunun kendi büyüklüğü (68x60)
                
                t = date(self.simdiki_yil, self.simdiki_ay, gun)
                v = vardiya_bul(t)
                renk = VARDİYA_RENKLERİ.get(v, "white"); tag = f"d_{gun}"
                
                # Kutuyu Çiz
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=renk, 
                                           outline="black" if self.secili_tarih == t else "#BBB", 
                                           width=4 if self.secili_tarih == t else 1, tags=tag)
                
                # GÜN NUMARASI (Kutu içinde merkeze aldık)
                self.canvas.create_text(x1+34, y1+20, text=str(gun), 
                                       font=("Segoe UI", 14, "bold"), 
                                       fill="white" if v in [1, 3] else "black", tags=tag)
                
                # VARDİYA YAZISI (G), (1), (2) vb.
                v_yazi = "(G)" if v == "Gündüz" else f"({v})"
                self.canvas.create_text(x1+34, y1+42, text=v_yazi, 
                                       font=("Segoe UI", 11, "bold"), 
                                       fill="white" if v in [1, 3] else "black", tags=tag)

    def tiklama(self, event):
        item = self.canvas.find_closest(event.x, event.y); tags = self.canvas.gettags(item)
        for t in tags:
            if t.startswith("d_"):
                g = int(t.split("_")[1]); self.secili_tarih = date(self.simdiki_yil, self.simdiki_ay, g); self.ciz(); self.callback(self.secili_tarih); break
    def ay_ileri(self):
        if self.simdiki_ay == 12: self.simdiki_ay = 1; self.simdiki_yil += 1
        else: self.simdiki_ay += 1
        self.ciz()
    def ay_geri(self):
        if self.simdiki_ay == 1: self.simdiki_ay = 12; self.simdiki_yil -= 1
        else: self.simdiki_ay -= 1
        self.ciz()

class IzinSistemi:
    def __init__(self, root):
        self.root = root
        
        # Sadece ilk açılış için çok kısa bir süre şeffaf başla
        self.root.attributes("-alpha", 0.0)
        
        self.root.title("Seydişehir İtfaiyesi - Personel Takip v7.5.9_NK")
        pencere_ortala(self.root, 1550, 900)
        self.root.configure(bg="#E0E0E0")
        
        self.root.protocol("WM_DELETE_WINDOW", self.guvenli_kapat)
        
        veritabani_kur()
        self.bas_tarih = self.bit_tarih = self.aktif_secim = self.secili_personel_id = None
        
        self.arayuz_olustur()
        self.listele()
        self.bayram_listele()

        # Program tamamen hazır olduktan 300ms sonra göster
        # Başka hiçbir bind (Map, Visibility vb.) eklemiyoruz!
        self.root.after(300, lambda: self.root.attributes("-alpha", 1.0))

    def arayuz_olustur(self):
	# --- COMBOBOX FONT VE STİL AYARLARI ---
        style = ttk.Style()
        
        # 1. Açılan liste (pop-up) içindeki yazıların fontunu büyütür
        self.root.option_add("*TCombobox*Listbox.font", ("Arial", 14)) 
        
        # 2. Combobox ayarı: Yazıyı büyütür ve içini bembeyaz yapar
        style.configure("TCombobox", font=("Arial", 14))
        style.map("TCombobox", 
                  fieldbackground=[("readonly", "white"), ("active", "white")],
                  background=[("readonly", "white"), ("active", "white")])
        # ---------------------------------------
        frame_mavi = "#4682B4"
        
        # 1. YENİ MAVİ ÇERÇEVE (Yuvarlak Köşeli)
        f_kayit = ctk.CTkFrame(self.root, corner_radius=20, 
                               fg_color=frame_mavi, 
                               bg_color="transparent")
        f_kayit.pack(fill="x", padx=20, pady=10)

        # 2. BAŞLIK (LabelFrame'in üzerindeki yazı yerine içeri ekliyoruz)
        self.lbl_kayit_baslik = ctk.CTkLabel(f_kayit, text=" Personel Kayıt ", 
                                            font=("Segoe UI", 16, "bold"), 
                                            text_color="white")
        self.lbl_kayit_baslik.grid(row=0, column=0, columnspan=12, sticky="w", padx=15, pady=(5, 0))

        # 3. ETİKETLER VE GİRİŞ KUTULARI (Hepsini row=1 yaptık)
        
        # --- SİCİL ---
        self.lbl_sicil = ctk.CTkLabel(f_kayit, text="Sicil:", corner_radius=10, fg_color="#B71C1C", 
                                      text_color="white", bg_color=frame_mavi, font=("Segoe UI", 14, "bold"), width=55)
        self.lbl_sicil.grid(row=1, column=0, padx=5, pady=10)
        
        self.ent_sicil = ctk.CTkEntry(f_kayit, width=100, font=("Arial", 16),
                                      fg_color="white", text_color="black", 
                                      border_color="white", border_width=0, # Dış çizgiyi temizledik
                                      corner_radius=10)
        self.ent_sicil.grid(row=1, column=1, padx=5, pady=10)

        # --- AD SOYAD ---
        self.lbl_isim = ctk.CTkLabel(f_kayit, text="Ad Soyad:", corner_radius=10, fg_color="#B71C1C", 
                                     text_color="white", bg_color=frame_mavi, font=("Segoe UI", 14, "bold"), width=55)
        self.lbl_isim.grid(row=1, column=2, padx=5, pady=10)
        
        self.ent_isim = ctk.CTkEntry(f_kayit, width=220, font=("Arial", 16),
                                     fg_color="white", text_color="black", 
                                     border_color="white", border_width=0, # Dış çizgiyi temizledik
                                     corner_radius=10)
        self.ent_isim.grid(row=1, column=3, padx=5, pady=10)

        # --- HAKEDİŞ TARİHİ ---
        self.lbl_hakedis = ctk.CTkLabel(f_kayit, text="Hakediş:", corner_radius=10, fg_color="#B71C1C", 
                                        text_color="white", bg_color=frame_mavi, font=("Segoe UI", 14, "bold"), width=55)
        self.lbl_hakedis.grid(row=1, column=4, padx=5, pady=10)
        
        self.ent_hak_tar = ctk.CTkEntry(f_kayit, width=120, font=("Arial", 16),
                                        fg_color="white", text_color="black", 
                                        border_color="white", border_width=0, # Dış çizgiyi temizledik
                                        corner_radius=10)
        self.ent_hak_tar.grid(row=1, column=5, padx=5, pady=10)

        # --- HAK ---
        self.lbl_hak = ctk.CTkLabel(f_kayit, text="Hak:", corner_radius=10, fg_color="#B71C1C", 
                                    text_color="white", bg_color=frame_mavi, font=("Segoe UI", 14, "bold"), width=55)
        self.lbl_hak.grid(row=1, column=6, padx=5, pady=10)
        
        self.ent_hak = ctk.CTkEntry(f_kayit, width=60, font=("Arial", 16),
                                    fg_color="white", text_color="black", 
                                    border_color="white", border_width=0, # Dış çizgiyi temizledik
                                    corner_radius=10)
        self.ent_hak.grid(row=1, column=7, padx=5, pady=10)

        # --- STATÜ ---
        self.lbl_statu = ctk.CTkLabel(f_kayit, text="Statü:", corner_radius=10, 
                                      fg_color="#B71C1C", text_color="white", bg_color=frame_mavi, 
                                      font=("Segoe UI", 14, "bold"), width=55)
        self.lbl_statu.grid(row=1, column=8, padx=1, pady=10)

        self.cmb_statu = ctk.CTkComboBox(f_kayit, 
                                         values=["Memur", "Şirket İşçisi(4A)"],
                                         width=140,
                                         font=("Segoe UI", 14),
                                         fg_color="white", 
                                         text_color="black",
                                         button_color="#B71C1C", 
                                         button_hover_color="#8B0000",
                                         border_color="white",
                                         border_width=0,
                                         corner_radius=10,
                                         state="readonly",
                                         # YENİ EKLENENLER:
                                         cursor="hand2",             # Mause el işareti olur
                                         dropdown_fg_color="white",  # Açılan liste bembeyaz olur
                                         dropdown_text_color="black",# Liste yazıları siyah olur
                                         dropdown_hover_color="#f0f0f0") # Üstüne gelince çok hafif grileşir
        self.cmb_statu.set("Memur")
        self.cmb_statu.grid(row=1, column=9, padx=1, pady=10)

        # --- VARDİYA ---
        self.lbl_vardiya_bas = ctk.CTkLabel(f_kayit, text="Vardiya:", corner_radius=10, 
                                            fg_color="#B71C1C", text_color="white", bg_color=frame_mavi, 
                                            font=("Segoe UI", 14, "bold"), width=55)
        self.lbl_vardiya_bas.grid(row=1, column=10, padx=1, pady=10)

        self.cmb_vardiya = ctk.CTkComboBox(f_kayit, 
                                           values=["1", "2", "3", "Gündüz"],
                                           width=92,
                                           font=("Arial", 14),
                                           fg_color="white", 
                                           text_color="black",
                                           button_color="#B71C1C", 
                                           button_hover_color="#8B0000",
                                           border_color="white",
                                           border_width=0,
                                           corner_radius=10,
                                           state="readonly",
                                           # YENİ EKLENENLER:
                                           cursor="hand2",             # Mause el işareti olur
                                           dropdown_fg_color="white",  # Açılan liste bembeyaz olur
                                           dropdown_text_color="black",
                                           dropdown_hover_color="#f0f0f0")
        self.cmb_vardiya.set("1")
        self.cmb_vardiya.grid(row=1, column=11, padx=1, pady=10)

        # --- BUTONLAR ---
        # 1. Önce Butonları Tanımlıyoruz
        self.btn_kaydet = ctk.CTkButton(f_kayit, text="KAYDET", command=self.personel_ekle,
                                        fg_color="#4CAF50", hover_color="#1B5E20", text_color="white",
                                        font=("Segoe UI", 15, "bold"), width=100)
        
        self.btn_guncelle = ctk.CTkButton(f_kayit, text="GÜNCELLE", command=self.personel_guncelle,
                                          fg_color="#E65100", hover_color="#EF6C00", text_color="white",
                                          font=("Segoe UI", 15, "bold"), width=100)

        # 2. Şimdi Butonları Ekrana Diziyoruz (Vardiyanın sağına)
        self.btn_kaydet.grid(row=1, column=12, padx=13, pady=13)
        self.btn_guncelle.grid(row=1, column=13, padx=13, pady=13)

        f_orta = tk.Frame(self.root, bg="#E0E0E0"); f_orta.pack(fill="x", padx=20, pady=5)
        self.takvim = OzelTakvim(f_orta, self.tarih_secildi); self.takvim.pack(side="left", padx=(0, 20))
        
        # 1. SAĞ İŞLEM ÇERÇEVESİ
        f_islem_sag = tk.Frame(f_orta, bg="#E0E0E0")
        f_islem_sag.pack(side="left", fill="both", expand=True)

        # 2. YUVARLAK KÖŞELİ KIRMIZI KUTU
        f_izin_kutu = ctk.CTkFrame(f_islem_sag, corner_radius=15, 
                                  fg_color="#B71C1C", 
                                  bg_color="#E0E0E0") 
        f_izin_kutu.pack(fill="x", padx=4, pady=1)

        # 3. BAŞLIK (Hata vermeyen, garantili yöntem)
        self.lbl_izin_baslik = ctk.CTkLabel(f_izin_kutu, 
                                           text="  İzin Talebi Oluştur ", 
                                           font=("Arial", 16, "bold"), 
                                           text_color="white")
        
        # Sola yaslamaya devam ediyoruz
        self.lbl_izin_baslik.grid(row=0, column=0, columnspan=5, sticky="w", padx=8, pady=(3, 0))
        
        # Başlangıç Butonu
        self.btn_bas = ctk.CTkButton(f_izin_kutu, 
                                     text="BAŞLANGIÇ", 
                                     command=lambda: self.tarih_ata(1),
                                     width=140,          
                                     height=38,          # Bir tık yükselttik (daha etli durur)
                                     corner_radius=10,   
                                     fg_color="#FFFFFF", # Kar beyazı
                                     text_color="#8B0000", # Koyu kırmızı yazı
                                     
                                     # BUTON HAVASI KATAN KRİTİK AYARLAR:
                                     border_width=4,      # Çerçeveyi kalınlaştırdık
                                     border_color="#FF6700", # Koyu kırmızı çerçeve (derinlik sağlar)
                                     hover_color="#EEEEEE", # Üzerine gelince belirginleşen gölge
                                     
                                     font=("Segoe UI", 15, "bold"))
        self.btn_bas.grid(row=1, column=0, pady=13, padx=8)

        # Başlangıç Tarih Etiketi (Standart tk.Label yerine ctk kullanabilirsin)
        self.lbl_bas = tk.Label(f_izin_kutu, 
                                text=" --.--.----", 
                                fg="#0D47A1", 
                                font=("Consolas", 18, "bold"), 
                                bg="white", 
                                width=12)
        self.lbl_bas.grid(row=1, column=1, padx=5)
        
        # Bitiş Butonu
        self.btn_bit = ctk.CTkButton(f_izin_kutu, 
                                     text="BİTİŞ", 
                                     command=lambda: self.tarih_ata(2),
                                     width=140,
                                     height=38,
                                     corner_radius=10,
                                     fg_color="#FFFFFF",
                                     text_color="#8B0000",
                                     
                                     # BUTON HAVASI KATAN KRİTİK AYARLAR:
                                     border_width=4,      # Çerçeveyi kalınlaştırdık
                                     border_color="#FF6700", 
                                     hover_color="#EEEEEE",
                                     
                                     font=("Segoe UI", 15, "bold"))
        self.btn_bit.grid(row=1, column=2, pady=13, padx=8)

        # Bitiş Tarih Etiketi
        self.lbl_bit = tk.Label(f_izin_kutu, 
                                text=" --.--.----", 
                                fg="#0D47A1", 
                                font=("Consolas", 18, "bold"), 
                                bg="white", 
                                width=12)
        self.lbl_bit.grid(row=1, column=3, padx=5)
        
        # HESAPLA VE KAYDET Butonu (Modernleşmiş Hali)
        # fg_color olarak COLORS["mavi"] kullanıyoruz, üzerine gelince biraz koyulaşması için hover_color ekledik.
        self.btn_hesapla = ctk.CTkButton(f_izin_kutu, text="HESAPLA VE KAYDET", 
                                         command=self.hesapla_ve_onayla, 
                                         fg_color="#0D47A1", 
                                         hover_color="#1565C0", # Başına # eklemeyi unutma (Hata verebilir)
                                         text_color="white", 
                                         # --- EKLEDİĞİMİZ KISIM BURASI ---
                                         border_width=2,         # Kenarlık kalınlığı (2 idealdir)
                                         border_color="#FFFAFA", # Kar beyazı renk kodu
                                         # -------------------------------
                                         font=("Segoe UI", 16, "bold"), 
                                         height=50, 
                                         corner_radius=12)
        
        # Grid yerleşimi (Önceki butonlarla aynı satırda kalması için row=1)
        self.btn_hesapla.grid(row=1, column=4, padx=20, pady=10)

        # --- BUTON PANELİ (MODERN YUVARLAK KÖŞELİ) ---
        # f_islem_sag'ın rengine uyum sağlaması için bg_color="#E0E0E0" yaptık
        f_btns = ctk.CTkFrame(f_islem_sag, fg_color="transparent", bg_color="#E0E0E0")
        f_btns.pack(fill="x", pady=10)

        # --- Ortak stil ayarları ---
        btn_font = ("Arial", 14, "bold")
        btn_h = 45  
        rad = 12    
        txt_c = "white"
        
        # --- YENİ KENARLIK AYARLARI ---
        b_width = 2             # Kenarlık kalınlığı
        b_color = "#FFFAFA"     # Kar beyazı renk kodu
        # -----------------------------

        # Butonlar
        ctk.CTkButton(f_btns, text="PERSONEL ARŞİVİ", command=self.arsiv_penceresi, 
                      fg_color=COLORS["arsiv"], text_color=txt_c, font=btn_font, 
                      border_width=b_width, border_color=b_color, # <-- Eklendi
                      corner_radius=rad, height=btn_h).pack(side="left", fill="x", expand=True, padx=2)

        ctk.CTkButton(f_btns, text="DEVİR YÖNETİMİ", command=self.devir_penceresi, 
                      fg_color="#C66900", text_color=txt_c, font=btn_font, 
                      border_width=b_width, border_color=b_color, # <-- Eklendi
                      corner_radius=rad, height=btn_h).pack(side="left", fill="x", expand=True, padx=2)

        ctk.CTkButton(f_btns, text="MAZERET İZNİ", command=self.mazeret_penceresi, 
                      fg_color=COLORS["mazeret"], text_color=txt_c, font=btn_font, 
                      border_width=b_width, border_color=b_color, # <-- Eklendi
                      corner_radius=rad, height=btn_h).pack(side="left", fill="x", expand=True, padx=2)

        ctk.CTkButton(f_btns, text="RAPOR YÖNETİMİ", command=self.rapor_penceresi, 
                      fg_color=COLORS["rapor"], text_color=txt_c, font=btn_font, 
                      border_width=b_width, border_color=b_color, # <-- Eklendi
                      corner_radius=rad, height=btn_h).pack(side="left", fill="x", expand=True, padx=2)

        ctk.CTkButton(f_btns, text="EXCEL'E AKTAR", command=self.excel_aktar, 
                      fg_color=COLORS["excel"], text_color=txt_c, font=btn_font, 
                      border_width=b_width, border_color=b_color, # <-- Eklendi
                      corner_radius=rad, height=btn_h).pack(side="left", fill="x", expand=True, padx=2)

        ctk.CTkButton(f_btns, text="PERSONEL SİL", command=self.personel_sil, 
                      fg_color=COLORS["sil"], text_color=txt_c, font=btn_font, 
                      border_width=b_width, border_color=b_color, # <-- Eklendi
                      corner_radius=rad, height=btn_h).pack(side="left", fill="x", expand=True, padx=2)
        # --- DİNİ BAYRAM MANUEL TANIMLAMA ALANI ---
        self.f_bayram = tk.LabelFrame(f_islem_sag, text=" 🌙 Dini Bayram Manuel Tanımlama ", 
                                     font=("Segoe UI", 13, "bold"), bg="#f1f1f1", padx=15, pady=10)
        self.f_bayram.pack(fill="x", pady=3, expand=True)

        self.f_bayram.columnconfigure(1, weight=1)
        self.f_bayram.columnconfigure(5, weight=0)

        tk.Label(self.f_bayram, text="Bayram Adı:", bg="#f1f1f1", font=LBL_FONT).grid(row=0, column=0, sticky="w")
        self.ent_bay_ad = tk.Entry(self.f_bayram, font=ENT_FONT)
        self.ent_bay_ad.grid(row=0, column=1, padx=5, sticky="ew")

        tk.Label(self.f_bayram, text="Tarih:", bg="#f1f1f1", font=LBL_FONT).grid(row=0, column=2, padx=(10,0))
        self.cal_bay = DateEntry(self.f_bayram, width=12, background='darkblue', 
                                 foreground='white', borderwidth=2, locale='tr_TR', font=ENT_FONT)
        self.cal_bay.grid(row=0, column=3, padx=5)
        
        tk.Button(self.f_bayram, text="KAYDET", command=self.bayram_ekle, 
                  bg="#2E7D32", fg="white", font=("Segoe UI", 11, "bold"), width=10).grid(row=0, column=4, padx=5)

        self.bay_tree = ttk.Treeview(self.f_bayram, columns=("id", "ad", "tar"), show="headings", height=5)
        self.bay_tree.heading("id", text="ID"); self.bay_tree.heading("ad", text="Bayram Adı"); self.bay_tree.heading("tar", text="Tarih")
        self.bay_tree.column("id", width=60, anchor="center"); self.bay_tree.column("ad", width=300, anchor="w"); self.bay_tree.column("tar", width=120, anchor="center")
        self.bay_tree.grid(row=1, column=0, columnspan=4, pady=5, sticky="nsew")

        tk.Button(self.f_bayram, text="SİL", command=self.bayram_sil, 
                  bg="#C62828", fg="white", font=("Segoe UI", 11, "bold"), width=10).grid(row=1, column=4, padx=5, sticky="n", pady=3)

        self.log_frame = tk.LabelFrame(self.f_bayram, text=" -- Sistem Hareketleri -- ", 
                               font=("Arial", 11, "bold"), bg="#fafafa", padx=10, pady=5)
        self.log_frame.grid(row=0, column=5, rowspan=2, padx=(15, 0), sticky="nsew")

        scrollbar = tk.Scrollbar(self.log_frame)
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(self.log_frame, width=85, height=8, font=("Consolas", 10), 
                                bg="#212121", fg="white", yscrollcommand=scrollbar.set)
        self.log_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        # --- LOG YÜKLEME ---
        try:
            if os.path.exists("log.txt"):
                with open("log.txt", "r", encoding="utf-8") as f:
                    for satir in f:
                        self.log_text.insert("end", satir)
                self.log_text.see("end")
        except:
            pass

        # --- ALT PERSONEL LİSTESİ ---
        cols = ("id", "sicil", "isim", "hakedis", "statu", "vardiya", "ana_hak", "devir", "kul", "rap", "kalan")
        
        style = ttk.Style()
        style.theme_use("clam") 
        
        style.configure("Treeview", 
                        font=("Segoe UI", 12), 
                        rowheight=35,
                        background="#FFFFFF",
                        foreground="black",
                        fieldbackground="#FFFFFF")

        style.configure("Treeview.Heading", 
                        background="#8B0000", 
                        foreground="white", 
                        font=("Segoe UI", 13, "bold"),
                        relief="flat")

        style.map("Treeview.Heading",
                  background=[('active', '#A52A2A')])
        
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings")
        heads = ["ID", "SİCİL", "AD SOYAD", "HAKEDİŞ", "STATÜ", "VARDİYA", "ANA HAK", "DEVİR", "KULLANILAN", "RAPOR", "KALAN"]
        
        for i, c in enumerate(cols):
            self.tree.heading(c, text=heads[i])
            self.tree.column(c, width=95, anchor="center")
        
        self.tree.column("isim", width=180, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=20, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.personel_secildi)

    def log_yaz(self, mesaj):
        # Sadece %H:%M:%S olan formatı %d.%m.%Y %H:%M:%S olarak değiştirdik
        zaman = datetime.now().strftime("%d.%m.%Y %H:%M:%S") 
        satir = f"[{zaman}] {mesaj}\n"
        
        # Text ekranına yaz 
        self.log_text.insert("end", satir)
        self.log_text.see("end")
        
        # Dosyaya da yaz [cite: 44]
        with open("log.txt", "a", encoding="utf-8") as f:
            f.write(satir)


    def bayram_ekle(self):
        ad = self.ent_bay_ad.get()
        tar = self.cal_bay.get_date().strftime("%d/%m/%Y")  # Formatı sabitle
        if ad and tar:
            try:
                conn = sqlite3.connect("itfaiye_izin.db")
                cur = conn.cursor()
                cur.execute("INSERT INTO manuel_bayramlar (ad, tarih) VALUES (?, ?)", (ad.upper(), tar))
                conn.commit()
                conn.close()
                self.bayram_listele()
                self.ent_bay_ad.delete(0, tk.END)
                self.log_yaz(f"Yeni bayram eklendi: {ad} - {tar}")
            except sqlite3.IntegrityError:
                messagebox.showerror("Hata", "Bu tarih zaten kayıtlı!")
            except Exception as e:
                messagebox.showerror("Hata", str(e))


    def bayram_listele(self):
        for i in self.bay_tree.get_children(): self.bay_tree.delete(i)
        conn = sqlite3.connect("itfaiye_izin.db"); cur = conn.cursor()
        cur.execute("SELECT * FROM manuel_bayramlar ORDER BY id DESC")
        for r in cur.fetchall(): self.bay_tree.insert("", "end", values=r)
        conn.close()

    def bayram_sil(self):
        s = self.bay_tree.selection()
        if s:
            conn = sqlite3.connect("itfaiye_izin.db"); cur = conn.cursor()
            cur.execute("DELETE FROM manuel_bayramlar WHERE id=?", (self.bay_tree.item(s)['values'][0],))
            conn.commit(); conn.close(); self.bayram_listele()

    def listele(self):
        self.otomatik_hakedis_islet()
        for i in self.tree.get_children(): 
            self.tree.delete(i)

        conn = sqlite3.connect("itfaiye_izin.db")
        cur = conn.cursor()

        cur.execute("SELECT id, sicil_no, isim, statu, vardiya, toplam_hak, hakedis_tarihi FROM personel ORDER BY isim ASC")

        for p in cur.fetchall():
            pid = p[0]
            statu = p[3]

            # Devir toplamı hesaplama
            if statu == "Memur":
                cur.execute("SELECT SUM(kalan_gun) FROM devir_izinler WHERE personel_id = ? AND yil >= ?", 
                           (pid, SU_AN_YIL - 1))
            else:
                cur.execute("SELECT SUM(kalan_gun) FROM devir_izinler WHERE personel_id = ?", (pid,))

            devir_toplam = cur.fetchone()[0] or 0

            cur.execute("SELECT SUM(harcanan_gun) FROM izinler WHERE personel_id = ?", (pid,))
            kul = cur.fetchone()[0] or 0

            cur.execute("SELECT SUM(gun_sayisi) FROM raporlar WHERE personel_id = ?", (pid,))
            rap = cur.fetchone()[0] or 0

            kalan = devir_toplam

            # Excel için yıl bazında detay
            if statu == "Memur":
                cur.execute("SELECT yil, kalan_gun FROM devir_izinler WHERE personel_id = ? AND yil >= ? ORDER BY yil", 
                           (pid, SU_AN_YIL - 1))
            else:
                cur.execute("SELECT yil, kalan_gun FROM devir_izinler WHERE personel_id = ? ORDER BY yil", (pid,))
            
            devir_list = cur.fetchall()

            values = (pid, p[1], p[2], p[6], statu, p[4], p[5], devir_toplam, kul, rap, kalan)
            self.tree.insert("", "end", values=values, tags=(str(devir_list),))

        conn.close()

    def otomatik_hakedis_islet(self):
        bugun = date.today()
        yil = bugun.year
        conn = sqlite3.connect("itfaiye_izin.db")
        cur = conn.cursor()

        # İsim bilgisini de çekiyoruz
        cur.execute("SELECT id, isim, hakedis_tarihi, toplam_hak, statu FROM personel")
        
        for p in cur.fetchall():
            pid, isim, h_tar_str, t_hak, statu = p[0], p[1], p[2], p[3], p[4]
            
            if not h_tar_str or h_tar_str in ["None", ""]:
                continue

            try:
                if '/' in h_tar_str:
                    h_gun, h_ay, _ = map(int, h_tar_str.split('/'))
                else:
                    h_gun, h_ay, _ = map(int, h_tar_str.split('.'))

                hakedis_tarihi_bu_yil = date(yil, h_ay, h_gun)

                if statu == "Memur":
                    # Memur için eski devirleri temizle (2 yıldan eski)
                    cur.execute("""
                        DELETE FROM devir_izinler 
                        WHERE personel_id = ? AND yil < ?
                    """, (pid, yil - 1))

                    # Bu yıl hakediş daha önce eklenmiş mi?
                    cur.execute("SELECT id FROM hakedis_takip WHERE personel_id=? AND yil=?", (pid, yil))
                    
                    if not cur.fetchone() and bugun >= hakedis_tarihi_bu_yil:
                        cur.execute("INSERT INTO devir_izinler (personel_id, yil, kalan_gun) VALUES (?,?,?)", 
                                   (pid, yil, t_hak))
                        cur.execute("INSERT INTO hakedis_takip (personel_id, yil) VALUES (?,?)", (pid, yil))
                        
                        # DÜZELTİLMİŞ LOG
                        self.log_yaz(f"Memur yeni hakediş eklendi → {isim}, {yil} yılı {t_hak} gün")

                else:
                    # İşçi için normal hakediş
                    cur.execute("SELECT id FROM hakedis_takip WHERE personel_id=? AND yil=?", (pid, yil))
                    if not cur.fetchone() and bugun >= hakedis_tarihi_bu_yil:
                        cur.execute("INSERT INTO devir_izinler (personel_id, yil, kalan_gun) VALUES (?,?,?)", 
                                   (pid, yil, t_hak))
                        cur.execute("INSERT INTO hakedis_takip (personel_id, yil) VALUES (?,?)", (pid, yil))
                        
                        # DÜZELTİLMİŞ LOG
                        self.log_yaz(f"İşçi yeni hakediş eklendi → {isim}, {yil} yılı {t_hak} gün")

            except:
                continue

        conn.commit()
        conn.close()

    def hesapla_ve_onayla(self):
        s = self.tree.selection()
        if not s or not self.bas_tarih or not self.bit_tarih:
            messagebox.showwarning("Uyarı", "Lütfen personel ve tarihleri seçin!"); return
        p = self.tree.item(s)['values']; pid = p[0]
        diff = (self.bit_tarih - self.bas_tarih).days + 1
        isbasi_tarihi = self.bit_tarih + timedelta(days=1)
        
        harcanan, pazar_sayisi, bayram_sayisi = 0, 0, 0
        bayram_listesi = []

        conn_b = sqlite3.connect("itfaiye_izin.db"); cur_b = conn_b.cursor()
        cur_b.execute("SELECT ad, tarih FROM manuel_bayramlar")
        manuel_b_dict = {r[1]: r[0] for r in cur_b.fetchall()}
        conn_b.close()
        
        for i in range(diff):
            t = self.bas_tarih + timedelta(days=i); t_str = t.strftime("%d/%m"); t_full_str = t.strftime("%d/%m/%Y")
            if "Memur" in str(p[4]): harcanan += 1
            else:
                if t.weekday() == 6: pazar_sayisi += 1
                elif t_str in RESMI_TATILLER: 
                    bayram_sayisi += 1; bayram_listesi.append(f"{t_full_str} - {TATIL_ADLARI[t_str]}")
                elif t_full_str in DINI_TATIL_DETAY:
                    bayram_sayisi += 1; bayram_listesi.append(f"{t_full_str} - {DINI_TATIL_DETAY[t_full_str]}")
                elif t_full_str in manuel_b_dict:
                    bayram_sayisi += 1; bayram_listesi.append(f"{t_full_str} - {manuel_b_dict[t_full_str]}")
                else: harcanan += 1
        
        if harcanan > p[10]:
            messagebox.showerror("Yetersiz Bakiye", f"Kalan: {p[10]}, Talep: {harcanan}"); return

        # --- BAKİYE DÖKÜMÜ ---
        c_tmp = sqlite3.connect("itfaiye_izin.db"); cur_tmp = c_tmp.cursor()
        if "Memur" in str(p[4]):
            cur_tmp.execute("SELECT yil, kalan_gun, id FROM devir_izinler WHERE personel_id=? AND yil >= ? ORDER BY yil ASC", (pid, SU_AN_YIL - 1))
        else:
            cur_tmp.execute("SELECT yil, kalan_gun, id FROM devir_izinler WHERE personel_id=? ORDER BY yil ASC", (pid,))
        
        rows = cur_tmp.fetchall(); temp_h = harcanan; yil_dokum = []; dusecek_plan = []
        for r_yil, r_kalan, r_id in rows:
            if temp_h <= 0: break
            if r_kalan <= 0: continue
            miktar = min(r_kalan, temp_h); yil_dokum.append(f"{r_yil} Yılından: {miktar} Gün"); dusecek_plan.append((r_id, miktar)); temp_h -= miktar
        c_tmp.close()

        # --- BURASI GERİ GELEN ÖZEL ONAY PENCERESİ ---
        win = tk.Toplevel(self.root); win.title("İzin Onay Detayı"); win.configure(bg="#f8f9fa")
        pencere_ortala(win, 650, 800); win.grab_set() 
        
        tk.Label(win, text="İZİN ÖZETİ VE HESAPLAMA DETAYI", font=("Segoe UI", 16, "bold"), bg=COLORS["koyu_mavi"], fg="white", pady=8).pack(fill="x")
        body = tk.Frame(win, bg="#f8f9fa", padx=30, pady=2); body.pack(fill="both", expand=True) 
        
        def satir(l, v, c="black", b=False):
            f = tk.Frame(body, bg="#f8f9fa"); f.pack(fill="x", pady=1)
            tk.Label(f, text=l, font=("Segoe UI", 13), bg="#f8f9fa", width=15, anchor="w").pack(side="left")
            tk.Label(f, text=v, font=("Segoe UI", 13, "bold" if b else "normal"), bg="#f8f9fa", fg=c).pack(side="left")
        
        satir("Personel:", p[2], b=True); satir("Statü:", p[4]); tk.Label(body, text="-"*40, bg="#f8f9fa").pack(pady=1)
        satir("Başlangıç:", self.bas_tarih.strftime("%d/%m/%Y"))
        satir("Bitiş:", self.bit_tarih.strftime("%d/%m/%Y"))
        satir("İŞBAŞI:", isbasi_tarihi.strftime("%d/%m/%Y"), c="#C62828", b=True)
        satir("Takvim Günü:", f"{diff} Gün")

        if "Memur" not in str(p[4]) and (pazar_sayisi > 0 or bayram_sayisi > 0):
            fb = tk.LabelFrame(body, text=" !!! TATİL GÜNÜ UYARISI !!! ", font=("Segoe UI", 13, "bold"), bg="#FFEBEE", fg="#B71C1C", padx=10, pady=5, bd=2)
            fb.pack(fill="x", pady=5)
            if pazar_sayisi > 0:
                tk.Label(fb, text=f"• {pazar_sayisi} GÜN PAZAR (DÜŞÜLMEZ)", font=("Segoe UI", 13, "bold"), bg="#FFEBEE", fg="#B71C1C").pack(anchor="w")
            if bayram_sayisi > 0:
                tk.Label(fb, text=f"• {bayram_sayisi} GÜN TATİL (DÜŞÜLMEZ)", font=("Segoe UI", 13, "bold"), bg="#FFEBEE", fg="#B71C1C").pack(anchor="w")
                for b_detay in bayram_listesi: 
                    tk.Label(fb, text=f"  - {b_detay}", font=("Segoe UI", 13), bg="#FFEBEE", fg="#333").pack(anchor="w")

        f_fifo = tk.LabelFrame(body, text=" Bakiye Kullanım Detayı ", bg="#FFFDE7", font=("Segoe UI", 12, "bold"), padx=10, pady=2, fg="#E65100")
        f_fifo.pack(fill="x", pady=2)
        for d in yil_dokum: tk.Label(f_fifo, text=d, bg="#FFFDE7", font=("Segoe UI", 13, "bold"), fg="#333").pack(anchor="w")

        tk.Label(body, text=f"HAKTAN DÜŞECEK: {harcanan} GÜN", font=("Segoe UI", 18, "bold"), fg=COLORS["mavi"], bg="#f8f9fa").pack(pady=5)

        def onay():
            c = sqlite3.connect("itfaiye_izin.db"); cur = c.cursor()
            cur.execute("INSERT INTO izinler (personel_id, baslangic, bitis, harcanan_gun, yil) VALUES (?,?,?,?,?)", 
                        (pid, self.bas_tarih.strftime("%d/%m/%Y"), self.bit_tarih.strftime("%d/%m/%Y"), harcanan, self.bas_tarih.year))
            iz_id = cur.lastrowid
            for d_id, miktar in dusecek_plan:
                cur.execute("UPDATE devir_izinler SET kalan_gun = kalan_gun - ? WHERE id = ?", (miktar, d_id))
                cur.execute("INSERT INTO izin_detaylari (izin_id, devir_id, miktar) VALUES (?,?,?)", (iz_id, d_id, miktar))
            c.commit(); c.close(); self.listele(); win.destroy()
            self.log_yaz(f"Yeni izin kaydı: Personel {p[2]} için {self.bas_tarih.strftime('%d/%m/%Y')} - {self.bit_tarih.strftime('%d/%m/%Y')} ({harcanan} gün)")
            messagebox.showinfo("Başarılı", "İzin kaydedildi.")

        btn_f = tk.Frame(win, bg="#f8f9fa", pady=5); btn_f.pack(side="bottom", fill="x")
        tk.Button(btn_f, text="ONAYLA VE BAKİYEDEN DÜŞ", command=onay, bg="#1B5E20", fg="white", font=("Segoe UI", 15, "bold"), pady=10, width=35).pack()

    def tarih_secildi(self, t): self.aktif_secim = t
    def tarih_ata(self, mod):
        if self.aktif_secim:
            if mod == 1: self.bas_tarih = self.aktif_secim; self.lbl_bas.config(text=self.bas_tarih.strftime("%d/%m/%Y"))
            elif mod == 2: self.bit_tarih = self.aktif_secim; self.lbl_bit.config(text=self.bit_tarih.strftime("%d/%m/%Y"))

    def personel_ekle(self):
        # --- GÜVENLİK DUVARI BAŞLANGICI ---
        sicil = self.ent_sicil.get().strip()
        isim = self.ent_isim.get().strip()

        if not sicil or not isim:
            messagebox.showwarning("Eksik Bilgi", "Lütfen Sicil No ve İsim alanlarını doldurun!")
            return 
        # --- GÜVENLİK DUVARI BİTİŞİ ---

        try:
            c = sqlite3.connect("itfaiye_izin.db"); cur = c.cursor()
            cur.execute("INSERT INTO personel (sicil_no, isim, statu, vardiya, toplam_hak, hakedis_tarihi) VALUES (?,?,?,?,?,?)", 
                        (sicil.upper(), isim.upper(), self.cmb_statu.get(), self.cmb_vardiya.get(), int(self.ent_hak.get() or 0), self.ent_hak_tar.get()))
            c.commit(); c.close(); self.listele()
            
            # Kayıt başarılı olduktan sonra kutuları temizlemek iyi olur:
            self.ent_sicil.delete(0, tk.END)
            self.ent_isim.delete(0, tk.END)
            
        except Exception as e: 
            messagebox.showerror("Hata", str(e))

    def personel_guncelle(self):
        if self.secili_personel_id:
            c = sqlite3.connect("itfaiye_izin.db"); cur = c.cursor()
            cur.execute("UPDATE personel SET sicil_no=?, isim=?, statu=?, vardiya=?, toplam_hak=?, hakedis_tarihi=? WHERE id=?", 
                        (self.ent_sicil.get().upper(), self.ent_isim.get().upper(), self.cmb_statu.get(), self.cmb_vardiya.get(), int(self.ent_hak.get() or 0), self.ent_hak_tar.get(), self.secili_personel_id))
            c.commit(); c.close(); self.listele()

    def mazeret_penceresi(self):
        s = self.tree.selection()
        if not s: return
        p = self.tree.item(s)['values']
        win = tk.Toplevel(self.root)
        win.title(f"Mazeret İzni: {p[2]}")
        pencere_ortala(win, 950, 700)
        
        # --- ANA ÇERÇEVE ---
        fu = tk.LabelFrame(win, bg="white", padx=10, pady=5)
        fu.pack(fill="x", padx=15, pady=10)

        # --- BÜYÜK BAŞLIK ---
        baslik_fontu = ("Segoe UI", 16, "bold")
        tk.Label(fu, 
                 text=" Yeni Mazeret İzni Kaydı (Haktan Düşmez) ", 
                 bg="white", 
                 fg="#8B0000", 
                 font=baslik_fontu).pack(anchor="w")

        # --- GİRİŞ ALANLARI İÇİN İÇ ÇERÇEVE (Grid hatasını önler) ---
        ic_f = tk.Frame(fu, bg="white")
        ic_f.pack(fill="x", pady=10)

        # Font ayarları
        etiket_f = ("Segoe UI", 14, "bold")
        giris_f = ("Segoe UI", 14)

        tk.Label(ic_f, text="Başlama:", bg="white", font=etiket_f).grid(row=0, column=0, padx=5)
        eb = tk.Entry(ic_f, width=12, font=giris_f)
        eb.insert(0, date.today().strftime("%d/%m/%Y"))
        eb.grid(row=0, column=1, padx=5)

        tk.Label(ic_f, text="Bitiş:", bg="white", font=etiket_f).grid(row=0, column=2, padx=5)
        ee = tk.Entry(ic_f, width=12, font=giris_f)
        ee.insert(0, date.today().strftime("%d/%m/%Y"))
        ee.grid(row=0, column=3, padx=5)

        tk.Label(ic_f, text="Açıklama:", bg="white", font=etiket_f).grid(row=0, column=4, padx=5)
        ea = tk.Entry(ic_f, width=20, font=giris_f)
        ea.grid(row=0, column=5, padx=5)

        def my(): # Tablo Yenileme
            for i in rt.get_children(): rt.delete(i)
            c = sqlite3.connect("itfaiye_izin.db"); cur = c.cursor()
            cur.execute("SELECT id, baslangic, bitis, gun_sayisi, aciklama FROM mazeret_izinleri WHERE personel_id=? ORDER BY id DESC", (p[0],))
            for r in cur.fetchall(): rt.insert("", "end", values=r)
            c.close()

        def me(): # Kaydetme
            try:
                b = datetime.strptime(eb.get(), "%d/%m/%Y")
                bit = datetime.strptime(ee.get(), "%d/%m/%Y")
                g = (bit - b).days + 1
                c = sqlite3.connect("itfaiye_izin.db"); cur = c.cursor()
                cur.execute("INSERT INTO mazeret_izinleri (personel_id, baslangic, bitis, gun_sayisi, aciklama) VALUES (?,?,?,?,?)", 
                            (p[0], eb.get(), ee.get(), g, ea.get().upper()))
                c.commit(); c.close(); self.listele(); my(); ea.delete(0, tk.END)
            except: 
                messagebox.showerror("Hata", "Format GG/AA/YYYY olmalı")

        tk.Button(ic_f, text="KAYDET", command=me, bg=COLORS["mazeret"], fg="white", font=("Arial", 11, "bold")).grid(row=0, column=6, padx=10)

        # --- TABLO ---
        rt = ttk.Treeview(win, columns=("id","b","bit","g", "ac"), show="headings")
        for c, h, w in zip(("id","b","bit","g", "ac"), ("ID","BAŞLANGIÇ", "BİTİŞ", "GÜN", "MAZERET NEDENİ"), (40, 100, 100, 50, 250)):
            rt.heading(c, text=h); rt.column(c, width=w, anchor="center")
        rt.pack(fill="both", expand=True, padx=15, pady=10)

        def ms(): # Silme
            sel = rt.selection()
            if sel and messagebox.askyesno("Onay", "Mazeret izni silinsin mi?"):
                c = sqlite3.connect("itfaiye_izin.db"); cur = c.cursor()
                cur.execute("DELETE FROM mazeret_izinleri WHERE id=?", (rt.item(sel)['values'][0],))
                c.commit(); c.close(); my(); self.listele()

        tk.Button(win, text="SEÇİLİ KAYDI SİL", command=ms, bg="#B71C1C", fg="white", font=LBL_FONT).pack(pady=5)
        
        my() # İlk yükleme

    def arsiv_penceresi(self):
        s = self.tree.selection()
        if not s: return
        p = self.tree.item(s)['values']; pid = p[0]
        win = tk.Toplevel(self.root); win.title(f"Arşiv: {p[2]}"); pencere_ortala(win, 1000, 600)
        ta = ttk.Treeview(win, columns=("id", "tip", "bas", "bit", "gun", "not"), show="headings")
        for c, h, w in [("id", "ID", 50), ("tip", "TÜR", 100), ("bas", "BAŞLANGIÇ", 120), ("bit", "BİTİŞ", 120), ("gun", "GÜN", 70), ("not", "AÇIKLAMA", 250)]:
            ta.heading(c, text=h); ta.column(c, width=w, anchor="w" if c=="not" else "center")
        ta.pack(fill="both", expand=True, padx=15, pady=15)
        def ay():
            for i in ta.get_children(): ta.delete(i)
            c = sqlite3.connect("itfaiye_izin.db"); cur = c.cursor()
            cur.execute("SELECT id, 'YILLIK', baslangic, bitis, harcanan_gun, 'Yıllık İzin' FROM izinler WHERE personel_id=?", (pid,))
            [ta.insert("", "end", values=r) for r in cur.fetchall()]
            cur.execute("SELECT id, 'MAZERET', baslangic, bitis, gun_sayisi, aciklama FROM mazeret_izinleri WHERE personel_id=?", (pid,))
            [ta.insert("", "end", values=r) for r in cur.fetchall()]
            cur.execute("SELECT id, 'RAPOR', baslangic, bitis, gun_sayisi, aciklama FROM raporlar WHERE personel_id=?", (pid,))
            [ta.insert("", "end", values=r) for r in cur.fetchall()]; c.close()
        def sa():
            sel = ta.selection()
            if not sel: return
            item = ta.item(sel)['values']
            iz_id, tur = item[0], item[1]
            p_isim = p[2] # Personel ismi üst fonksiyondan (personel_secildi) otomatik gelir

            if tur == "YILLIK":
                if messagebox.askyesno("Onay", "Yıllık izin silinsin mi? (Bakiye iade edilir)"):
                    c = sqlite3.connect("itfaiye_izin.db")
                    cur = c.cursor()
                    
                    # 1. ADIM: SİLMEDEN ÖNCE BİLGİLERİ AL (LOG İÇİN)
                    cur.execute("SELECT baslangic, bitis, harcanan_gun FROM izinler WHERE id=?", (iz_id,))
                    iz_bilgi = cur.fetchone()
                    
                    # 2. ADIM: BAKİYEYİ İADE ET (Mevcut kodunuz)
                    cur.execute("SELECT devir_id, miktar FROM izin_detaylari WHERE izin_id=?", (iz_id,))
                    for d_id, miktar in cur.fetchall():
                        cur.execute("UPDATE devir_izinler SET kalan_gun = kalan_gun + ? WHERE id = ?", (miktar, d_id))
                    
                    # 3. ADIM: KAYITLARI SİL (Mevcut kodunuz)
                    cur.execute("DELETE FROM izin_detaylari WHERE izin_id=?", (iz_id,))
                    cur.execute("DELETE FROM izinler WHERE id=?", (iz_id,))
                    
                    c.commit()
                    c.close()

                    # 4. ADIM: LOG EKRANINA YAZDIR (YENİ EKLENEN KISIM)
                    if iz_bilgi:
                        # iz_bilgi[0]=Başlangıç, [1]=Bitiş, [2]=Gün Sayısı
                        self.log_yaz(f"İPTAL: {p_isim} - {iz_bilgi[0]}/{iz_bilgi[1]} tarihli {iz_bilgi[2]} günlük izin silindi.")
                    
                    ay() # Tabloyu yenile
                    self.listele() # Ana ekranı güncelle
            else:
                messagebox.showinfo("Bilgi", f"{tur} kayıtlarını kendi yönetim menülerinden silebilirsiniz.")
        tk.Button(win, text="YILLIK İZNİ SİL VE İADE ET", command=sa, bg="#B71C1C", fg="white", font=LBL_FONT).pack(pady=5); ay()

    def devir_penceresi(self):
        s = self.tree.selection()
        if not s: return
        p = self.tree.item(s)['values']
        
        # --- 1. FONT TANIMLARI ---
        DEVIR_FONT = ("Segoe UI", 14, "bold")  # Etiketler (Yıl, Gün) için
        KUTU_FONT = ("Consolas", 14, "bold")   # Rakam girişleri için
        
        win = tk.Toplevel(self.root)
        win.title(f"Devir: {p[2]}")
        pencere_ortala(win, 550, 650) # Boyutu fontlara göre büyüttük
        
        # Üst Giriş Alanı
        f = tk.Frame(win, pady=20) 
        f.pack()
        
        # Yıl Bölümü (BÜYÜK ve ORTALI)
        tk.Label(f, text="Yıl:", font=DEVIR_FONT).grid(row=0, column=0, padx=5)
        ey = tk.Entry(f, width=8, font=KUTU_FONT, justify="center")
        ey.insert(0, str(SU_AN_YIL-1))
        ey.grid(row=0, column=1, padx=5)
        
        # Gün Bölümü (BÜYÜK ve ORTALI)
        tk.Label(f, text="Gün:", font=DEVIR_FONT).grid(row=0, column=2, padx=15)
        eg = tk.Entry(f, width=8, font=KUTU_FONT, justify="center")
        eg.grid(row=0, column=3, padx=5)

        # Alt Liste Alanı (Treeview)
        dt = ttk.Treeview(win, columns=("id", "y", "g"), show="headings", height=8)
        dt.heading("id", text="ID")
        dt.heading("y", text="YIL")
        dt.heading("g", text="GÜN")
        
        dt.column("id", width=50, anchor="center")
        dt.column("y", width=150, anchor="center")
        dt.column("g", width=150, anchor="center")
        
        dt.pack(padx=20, pady=10, fill="both", expand=True)

        def dy():
            for i in dt.get_children(): dt.delete(i)
            c = sqlite3.connect("itfaiye_izin.db")
            cur = c.cursor()
            cur.execute("SELECT id, yil, kalan_gun FROM devir_izinler WHERE personel_id=? ORDER BY yil DESC", (p[0],))
            [dt.insert("", "end", values=r) for r in cur.fetchall()]
            c.close()

        def de():
            y_val = ey.get()
            g_val = eg.get()
            if not y_val or not g_val:
                messagebox.showwarning("Uyarı", "Yıl ve Gün alanlarını doldurun!")
                return
                
            c = sqlite3.connect("itfaiye_izin.db")
            cur = c.cursor()
            cur.execute("INSERT INTO devir_izinler (personel_id, yil, kalan_gun) VALUES (?,?,?)", (p[0], y_val, g_val))
            c.commit()
            c.close()
            
            # LOG KAYDI: EKLEME
            self.log_yaz(f"DEVİR EKLEME: {p[2]} - {y_val} yılı için {g_val} gün devir hakkı tanımlandı.")
            
            dy()
            self.listele()

        def ds():
            sel = dt.selection()
            if sel:
                item = dt.item(sel)['values']
                d_id, d_yil, d_gun = item[0], item[1], item[2]
                
                if messagebox.askyesno("Onay", f"{d_yil} yılına ait {d_gun} günlük devir silinsin mi?"):
                    c = sqlite3.connect("itfaiye_izin.db")
                    cur = c.cursor()
                    cur.execute("DELETE FROM devir_izinler WHERE id=?", (d_id,))
                    c.commit()
                    c.close()
                    
                    # LOG KAYDI: SİLME
                    self.log_yaz(f"DEVİR SİLME: {p[2]} - {d_yil} yılına ait {d_gun} günlük devir kaydı silindi.")
                    
                    dy()
                    self.listele()

        # Gün Ekle/Düzenle Butonu
        ctk.CTkButton(win, 
                      text="GÜN EKLE/DÜZENLE", 
                      command=de, 
                      fg_color="#2E7D32",    # Koyu Yeşil
                      hover_color="#1B5E20", 
                      font=("Segoe UI", 14, "bold"), # Yazıyı büyüttük
                      height=35,             # Butonu kalınlaştırdık
                      corner_radius=15).pack(pady=10, padx=20, fill="x")

        # Seçili Deviri Sil Butonu
        ctk.CTkButton(win, 
                      text="SEÇİLİ DEVİRİ SİL", 
                      command=ds, 
                      fg_color="#C62828",    # Koyu Kırmızı
                      hover_color="#B71C1C", 
                      font=("Segoe UI", 14, "bold"), # Yazıyı büyüttük
                      height=35,             # Butonu kalınlaştırdık
                      corner_radius=15).pack(pady=5, padx=20, fill="x")
        
        dy() # Listeyi yenileyen fonksiyon

    def rapor_penceresi(self):
        s = self.tree.selection()
        if not s: return
        p = self.tree.item(s)['values']
        win = tk.Toplevel(self.root)
        win.title(f"Rapor: {p[2]}")
        pencere_ortala(win, 1000, 700)
        
        # --- ANA ÇERÇEVE ---
        fu = tk.LabelFrame(win, bg="white", padx=10, pady=5)
        fu.pack(fill="x", padx=25, pady=20)

        # --- BAŞLIK (PACK ile) ---
        baslik_yazisi = tk.Label(fu, 
                                 text=" Yeni Rapor Kaydı ", 
                                 bg="white", 
                                 fg="#8B0000", 
                                 font=("Segoe UI", 16, "bold"))
        baslik_yazisi.pack(anchor="w")

        # --- GİRİŞ ALANLARI İÇİN ARA ÇERÇEVE (GRID burada kullanılacak) ---
        # Bu yeni çerçeveyi 'fu' içine 'pack' ile koyuyoruz, böylece grid hatası almıyoruz.
        ic_grid_cerceve = tk.Frame(fu, bg="white")
        ic_grid_cerceve.pack(fill="x", pady=10)
        
       # Önce kullanacağın fontu belirle (Örn: Segoe UI, 12 punto, Kalın)
        giris_fontu = ("Segoe UI", 12, "bold")
        etiket_fontu = ("Segoe UI", 11)

	# --- FONT TANIMLAMALARI (Buradaki rakamları büyütebilirsin) ---
        etiket_fontu = ("Segoe UI", 14, "bold")  # 12'yi 14 yaparsan etiketler büyür
        giris_fontu = ("Segoe UI", 14)          # 14'ü 16 yaparsan yazılan rakamlar büyür

        # Bas Etiketi ve Girişi
        tk.Label(ic_grid_cerceve, text="Başlama:", bg="white", font=etiket_fontu).grid(row=0, column=0)
        eb = tk.Entry(ic_grid_cerceve, width=12, font=giris_fontu) # <-- Buraya eklendi
        eb.insert(0, date.today().strftime("%d/%m/%Y"))
        eb.grid(row=0, column=1, padx=5)
        
        # Bit Etiketi ve Girişi
        tk.Label(ic_grid_cerceve, text="Bitiş:", bg="white", font=etiket_fontu).grid(row=0, column=2)
        ee = tk.Entry(ic_grid_cerceve, width=12, font=giris_fontu) # <-- Buraya eklendi
        ee.insert(0, date.today().strftime("%d/%m/%Y"))
        ee.grid(row=0, column=3, padx=5)
        
        # Açıklama Etiketi ve Girişi
        tk.Label(ic_grid_cerceve, text="Açıklama:", bg="white", font=etiket_fontu).grid(row=0, column=4)
        ea = tk.Entry(ic_grid_cerceve, width=20, font=giris_fontu) # <-- Buraya eklendi
        ea.grid(row=0, column=5, padx=5)

        # Fonksiyonlar ve diğer kısımlar aynı kalıyor...
        def ry():
            for i in rt.get_children(): rt.delete(i)
            c = sqlite3.connect("itfaiye_izin.db"); cur = c.cursor()
            cur.execute("SELECT id, baslangic, bitis, gun_sayisi, aciklama FROM raporlar WHERE personel_id=? ORDER BY id DESC", (p[0],))
            for r in cur.fetchall():
                try:
                    bitis_obj = datetime.strptime(r[2], "%d/%m/%Y")
                    is_basi = (bitis_obj + timedelta(days=1)).strftime("%d/%m/%Y")
                except: is_basi = "Hata!"
                rt.insert("", "end", values=(r[0], r[1], r[2], is_basi, r[3], r[4]))
            c.close()

        def re():
            try:
                b = datetime.strptime(eb.get(), "%d/%m/%Y")
                bit = datetime.strptime(ee.get(), "%d/%m/%Y")
                if bit < b:
                    messagebox.showerror("Hata", "Bitiş tarihi başlangıçtan önce olamaz!")
                    return
                g = (bit - b).days + 1
                c = sqlite3.connect("itfaiye_izin.db"); cur = c.cursor()
                cur.execute("INSERT INTO raporlar (personel_id, baslangic, bitis, gun_sayisi, aciklama) VALUES (?,?,?,?,?)", 
                            (p[0], eb.get(), ee.get(), g, ea.get().upper()))
                c.commit(); c.close()
                self.listele(); ry(); ea.delete(0, tk.END)
            except: 
                messagebox.showerror("Hata", "Format GG/AA/YYYY olmalı")

        tk.Button(ic_grid_cerceve, text="KAYDET", command=re, bg="#1B5E20", fg="white", font=("Arial", 10, "bold")).grid(row=0, column=6, padx=10)

        # Tablo ve Silme Butonu aynı kalabilir
        rt = ttk.Treeview(win, columns=("id","b","bit","isb","g", "ac"), show="headings")
        sutunlar = [("id", "ID", 40), ("b", "BAŞLANGIÇ", 100), ("bit", "BİTİŞ", 100), ("isb", "İŞBAŞI", 100), ("g", "GÜN", 60), ("ac", "AÇIKLAMA", 200)]
        for c, h, w in sutunlar:
            rt.heading(c, text=h)
            rt.column(c, width=w, anchor="center")
        
        rt.pack(fill="both", expand=True, padx=15, pady=10)

        def rs():
            sel = rt.selection()
            if sel and messagebox.askyesno("Onay", "Seçili rapor silinsin mi?"):
                c = sqlite3.connect("itfaiye_izin.db"); cur = c.cursor()
                cur.execute("DELETE FROM raporlar WHERE id=?", (rt.item(sel)['values'][0],))
                c.commit(); c.close(); ry(); self.listele()

        tk.Button(win, text="SEÇİLİ RAPORU SİL", command=rs, bg="#B71C1C", fg="white", font=("Arial", 10, "bold"), pady=5).pack(pady=10)
        ry()

    def excel_aktar(self):
        if not self.tree.get_children():
            messagebox.showwarning("Uyarı", "Aktarılacak veri bulunamadı!")
            return

        data = []
        base_columns = ["ID", "SİCİL", "AD SOYAD", "HAKEDİŞ TARİHİ", "STATÜ", "VARDİYA", 
                        "ANA HAK", "TOPLAM DEVİR", "KULLANILAN", "RAPOR", "KALAN"]

        # Tüm devir yıllarını bul
        devir_yillari = set()
        for child in self.tree.get_children():
            tag = self.tree.item(child).get('tags')
            if tag and tag[0]:
                try:
                    devir_list = eval(tag[0])
                    for yil, _ in devir_list:
                        devir_yillari.add(int(yil))
                except:
                    pass

        devir_yillari = sorted(list(devir_yillari))
        columns = base_columns + [f"DEVİR {y}" for y in devir_yillari]

        # Satırları doldur
        for child in self.tree.get_children():
            item = self.tree.item(child)
            values = list(item['values'])   # ID, Sicil, İsim, ..., KALAN (devir_toplam)

            # Devir detaylarını yıl sütunlarına yerleştir
            devir_dict = {}
            tag = item.get('tags')
            if tag and tag[0]:
                try:
                    devir_list = eval(tag[0])
                    devir_dict = {int(yil): int(gun) for yil, gun in devir_list}
                except:
                    pass

            for y in devir_yillari:
                values.append(devir_dict.get(y, 0))

            data.append(values)

        df = pd.DataFrame(data, columns=columns)

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Dosyası", "*.xlsx"), ("Tüm Dosyalar", "*.*")]
        )

        if path:
            try:
                df.to_excel(path, index=False)
                messagebox.showinfo("Başarılı", f"Excel dosyası oluşturuldu:\n{path}")
            except Exception as e:
                messagebox.showerror("Hata", f"Excel kaydedilemedi: {str(e)}")

    def veritabanı_yedek_gonder(self):
        import os, smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders
        
        gonderen = "itfaiye.seydisehir@gmail.com"
        # Şifre tam 16 hane olmalı, aşağıdakini kopyala:
        sifre = "tnivewdfwrmqsggd" 
        alici = "itfaiye.seydisehir@gmail.com"
        dosya_adi = "itfaiye_izin.db"

        if not os.path.exists(dosya_adi):
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = gonderen
            msg['To'] = alici
            msg['Subject'] = f"İtfaiye İzin Sistemi Yedek - {datetime.now().strftime('%d.%m.%Y %H:%M')}"

            with open(dosya_adi, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename= {dosya_adi}")
                msg.attach(part)

            server = smtplib.SMTP('smtp.gmail.com', 587, timeout=15)
            server.starttls()
            server.login(gonderen, sifre)
            server.send_message(msg)
            server.quit()
        except Exception as e:
            print(f"Hata: {e}")

    def guvenli_kapat(self):
        try:
            # 1. Bilgilendirme Penceresini Oluştur
            self.yedek_ekrani = tk.Toplevel(self.root)
            self.yedek_ekrani.title("Sistem")
            self.yedek_ekrani.geometry("500x250")
            self.yedek_ekrani.attributes('-topmost', True)
            
            # --- KIRMIZI KENARLIK AYARLARI ---
            itfaiye_kirmizisi = "#D32F2F"
            self.yedek_ekrani.configure(bg=itfaiye_kirmizisi)
            
            # İç beyaz kutu
            ana_f = tk.Frame(self.yedek_ekrani, bg="white")
            ana_f.pack(fill="both", expand=True, padx=10, pady=10)

            # Konum Hesaplama
            x = self.root.winfo_x() + (self.root.winfo_width() // 3) -   0
            y = self.root.winfo_y() + (self.root.winfo_height() // 3) -  0
            self.yedek_ekrani.geometry(f"+{x}+{y}")
            
            # İçerik
            tk.Label(ana_f, text="\nVERİLER YEDEKLENİYOR...", font=("Arial", 15, "bold"), fg="#D32F2F", bg="white").pack()
            tk.Label(ana_f, text="VERİ DOSYASI MAİL ADRESİNE GÖNDERİLİYOR", font=("Arial", 15), bg="white").pack()
            tk.Label(ana_f, text="\nLütfen bekleyiniz...", font=("Arial", 12, "italic"), bg="white").pack()
            
            # Ekranı zorla güncelle (Donmayı önler)
            self.yedek_ekrani.update()
            self.root.update()

            # 2. Yedekleme Fonksiyonunu Çağır
            # Not: Fonksiyon isminde 'ı' harfi varsa 'i' ile değiştirmen gerekebilir (veritabani_yedek_gonder)
            self.veritabanı_yedek_gonder()
            
        except Exception as e:
            print(f"Kapatma hatası: {e}") # Hatayı konsolda gör ki neden açılmadığını anlayalım
        finally:
            self.root.destroy()

    def personel_sil(self):
        s = self.tree.selection()
        if not s:
            return
        
        p = self.tree.item(s)['values']
        pid = p[0]
        isim = p[2]

        if messagebox.askyesno("Onay", f"{isim} personelini ve tüm geçmişini silmek istediğinize emin misiniz?"):
            try:
                c = sqlite3.connect("itfaiye_izin.db")
                cur = c.cursor()
                
                # Silinen personelin bilgilerini log için al (opsiyonel ama güzel olur)
                cur.execute("SELECT sicil_no FROM personel WHERE id=?", (pid,))
                sicil = cur.fetchone()
                sicil_no = sicil[0] if sicil else "Bilinmiyor"

                # Personeli ve ilgili tüm kayıtlarını sil
                cur.execute("DELETE FROM personel WHERE id=?", (pid,))
                cur.execute("DELETE FROM izinler WHERE personel_id=?", (pid,))
                cur.execute("DELETE FROM devir_izinler WHERE personel_id=?", (pid,))
                cur.execute("DELETE FROM raporlar WHERE personel_id=?", (pid,))
                cur.execute("DELETE FROM mazeret_izinleri WHERE personel_id=?", (pid,))
                cur.execute("DELETE FROM hakedis_takip WHERE personel_id=?", (pid,))
                cur.execute("DELETE FROM izin_detaylari WHERE izin_id IN (SELECT id FROM izinler WHERE personel_id=?)", (pid,))
                
                c.commit()
                c.close()

                # Log'a yaz
                self.log_yaz(f"PERSONEL SİLİNDİ → {isim} (Sicil: {sicil_no}) ve tüm kayıtları silindi.")

                self.listele()
                messagebox.showinfo("Başarılı", f"{isim} personeli ve tüm geçmişi silindi.")

            except Exception as e:
                messagebox.showerror("Hata", f"Silme işlemi sırasında hata oluştu:\n{str(e)}")

    def personel_secildi(self, event):
        s = self.tree.selection()
        if s:
            p = self.tree.item(s)['values']; self.secili_personel_id = p[0]; self.ent_sicil.delete(0, tk.END); self.ent_sicil.insert(0, p[1]); self.ent_isim.delete(0, tk.END); self.ent_isim.insert(0, p[2]); self.ent_hak_tar.delete(0, tk.END); self.ent_hak_tar.insert(0, p[3]); self.cmb_statu.set(p[4]); self.cmb_vardiya.set(p[5]); self.ent_hak.delete(0, tk.END); self.ent_hak.insert(0, p[6])

if __name__ == "__main__":
    # tk.Tk() yerine ctk.CTk() kullanarak ana motoru hızlandırıyoruz
    root = ctk.CTk() 
    
    # Pencere henüz çizilmeden gizleyip, her şey hazır olunca tek seferde göstereceğiz
    root.withdraw() 
    
    app = IzinSistemi(root)
    root.protocol("WM_DELETE_WINDOW", app.guvenli_kapat)
    
    # Her şey yüklendi, şimdi pencereyi ekrana fırlat!
    root.after(0, root.deiconify) 
    
    root.mainloop()