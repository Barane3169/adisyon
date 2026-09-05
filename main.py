# -*- coding: utf-8 -*-
"""
ADİSYON SİSTEMİ
================
Masa açma/kapama, sipariş girme/silme/onaylama, ödeme alma ve
muhasebe (satış raporu, gider takibi) özelliklerine sahip masaüstü uygulama.

Gereksinimler: Sadece Python standart kütüphanesi (tkinter, sqlite3).
Çalıştırma:    python main.py
.exe yapma:    Bu dosyanın yanındaki README.md dosyasına bakın.
"""

import os
import sys
import sqlite3
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog


# ---------------------------------------------------------------------------
# Veritabanı dosyasının konumu (exe'ye çevrildiğinde exe ile aynı klasörde
# oluşur, böylece veriler kalıcı olur).
# ---------------------------------------------------------------------------
def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DB_PATH = os.path.join(get_base_dir(), "adisyon.db")

ODEME_YONTEMLERI = ["Nakit", "Kredi Kartı", "Yemek Kartı"]


# ---------------------------------------------------------------------------
# VERİTABANI KATMANI
# ---------------------------------------------------------------------------
class VeriTabani:
    def __init__(self, path=DB_PATH):
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        self._olustur()
        self._ornek_veri_ekle()

    # -- kurulum -----------------------------------------------------------
    def _olustur(self):
        c = self.conn.cursor()
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS masalar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad TEXT NOT NULL,
                durum TEXT NOT NULL DEFAULT 'bos'
            );

            CREATE TABLE IF NOT EXISTS urunler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad TEXT NOT NULL,
                kategori TEXT NOT NULL DEFAULT 'Genel',
                fiyat REAL NOT NULL,
                aktif INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS adisyonlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                masa_id INTEGER NOT NULL,
                acilis_zamani TEXT NOT NULL,
                kapanis_zamani TEXT,
                durum TEXT NOT NULL DEFAULT 'acik',
                FOREIGN KEY(masa_id) REFERENCES masalar(id)
            );

            CREATE TABLE IF NOT EXISTS adisyon_kalemleri (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adisyon_id INTEGER NOT NULL,
                urun_id INTEGER,
                urun_adi TEXT NOT NULL,
                birim_fiyat REAL NOT NULL,
                adet INTEGER NOT NULL,
                durum TEXT NOT NULL DEFAULT 'bekliyor',
                eklenme_zamani TEXT NOT NULL,
                FOREIGN KEY(adisyon_id) REFERENCES adisyonlar(id)
            );

            CREATE TABLE IF NOT EXISTS odemeler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adisyon_id INTEGER NOT NULL,
                yontem TEXT NOT NULL,
                tutar REAL NOT NULL,
                zaman TEXT NOT NULL,
                FOREIGN KEY(adisyon_id) REFERENCES adisyonlar(id)
            );

            CREATE TABLE IF NOT EXISTS giderler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aciklama TEXT NOT NULL,
                tutar REAL NOT NULL,
                tarih TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def _ornek_veri_ekle(self):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM masalar")
        if c.fetchone()[0] == 0:
            for i in range(1, 9):
                c.execute("INSERT INTO masalar (ad, durum) VALUES (?, 'bos')", (f"Masa {i}",))
        c.execute("SELECT COUNT(*) FROM urunler")
        if c.fetchone()[0] == 0:
            ornekler = [
                ("Çay", "İçecek", 15.0),
                ("Türk Kahvesi", "İçecek", 45.0),
                ("Ayran", "İçecek", 25.0),
                ("Kola", "İçecek", 40.0),
                ("Adana Kebap", "Yemek", 320.0),
                ("Izgara Köfte", "Yemek", 280.0),
                ("Mercimek Çorbası", "Yemek", 90.0),
                ("Karışık Pizza", "Yemek", 260.0),
                ("Baklava", "Tatlı", 120.0),
                ("Sütlaç", "Tatlı", 90.0),
            ]
            c.executemany(
                "INSERT INTO urunler (ad, kategori, fiyat) VALUES (?, ?, ?)", ornekler
            )
        self.conn.commit()

    @staticmethod
    def _simdi():
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # -- masalar -------------------------------------------------------------
    def masalari_getir(self):
        return self.conn.execute("SELECT * FROM masalar ORDER BY id").fetchall()

    def masa_ekle(self, ad):
        self.conn.execute("INSERT INTO masalar (ad, durum) VALUES (?, 'bos')", (ad,))
        self.conn.commit()

    def masa_sil(self, masa_id):
        acik = self.conn.execute(
            "SELECT COUNT(*) FROM adisyonlar WHERE masa_id=? AND durum='acik'", (masa_id,)
        ).fetchone()[0]
        if acik:
            raise ValueError("Bu masada açık adisyon var, önce kapatın.")
        self.conn.execute("DELETE FROM masalar WHERE id=?", (masa_id,))
        self.conn.commit()

    def masa_durum_guncelle(self, masa_id, durum):
        self.conn.execute("UPDATE masalar SET durum=? WHERE id=?", (durum, masa_id))
        self.conn.commit()

    # -- ürünler -------------------------------------------------------------
    def urunleri_getir(self, sadece_aktif=True):
        if sadece_aktif:
            return self.conn.execute(
                "SELECT * FROM urunler WHERE aktif=1 ORDER BY kategori, ad"
            ).fetchall()
        return self.conn.execute("SELECT * FROM urunler ORDER BY kategori, ad").fetchall()

    def urun_ekle(self, ad, kategori, fiyat):
        self.conn.execute(
            "INSERT INTO urunler (ad, kategori, fiyat) VALUES (?, ?, ?)", (ad, kategori, fiyat)
        )
        self.conn.commit()

    def urun_guncelle(self, urun_id, ad, kategori, fiyat):
        self.conn.execute(
            "UPDATE urunler SET ad=?, kategori=?, fiyat=? WHERE id=?",
            (ad, kategori, fiyat, urun_id),
        )
        self.conn.commit()

    def urun_sil(self, urun_id):
        # Geçmiş kalemlerin bütünlüğünü bozmamak için tamamen silmek yerine pasif yapılır.
        self.conn.execute("UPDATE urunler SET aktif=0 WHERE id=?", (urun_id,))
        self.conn.commit()

    # -- adisyon (sipariş) ----------------------------------------------------
    def acik_adisyon_getir(self, masa_id):
        return self.conn.execute(
            "SELECT * FROM adisyonlar WHERE masa_id=? AND durum='acik'", (masa_id,)
        ).fetchone()

    def masa_ac(self, masa_id):
        mevcut = self.acik_adisyon_getir(masa_id)
        if mevcut:
            return mevcut["id"]
        cur = self.conn.execute(
            "INSERT INTO adisyonlar (masa_id, acilis_zamani, durum) VALUES (?, ?, 'acik')",
            (masa_id, self._simdi()),
        )
        self.masa_durum_guncelle(masa_id, "dolu")
        self.conn.commit()
        return cur.lastrowid

    def siparis_ekle(self, adisyon_id, urun_id, urun_adi, birim_fiyat, adet):
        self.conn.execute(
            """INSERT INTO adisyon_kalemleri
               (adisyon_id, urun_id, urun_adi, birim_fiyat, adet, durum, eklenme_zamani)
               VALUES (?, ?, ?, ?, ?, 'bekliyor', ?)""",
            (adisyon_id, urun_id, urun_adi, birim_fiyat, adet, self._simdi()),
        )
        self.conn.commit()

    def siparis_kalemleri_getir(self, adisyon_id):
        return self.conn.execute(
            "SELECT * FROM adisyon_kalemleri WHERE adisyon_id=? AND durum != 'iptal' ORDER BY id",
            (adisyon_id,),
        ).fetchall()

    def kalem_sil(self, kalem_id):
        row = self.conn.execute(
            "SELECT durum FROM adisyon_kalemleri WHERE id=?", (kalem_id,)
        ).fetchone()
        if row is None:
            return
        if row["durum"] == "bekliyor":
            # Henüz onaylanmadıysa tamamen sil.
            self.conn.execute("DELETE FROM adisyon_kalemleri WHERE id=?", (kalem_id,))
        else:
            # Onaylanmışsa iz bırakmak için iptal olarak işaretle (muhasebe tutarlılığı).
            self.conn.execute(
                "UPDATE adisyon_kalemleri SET durum='iptal' WHERE id=?", (kalem_id,)
            )
        self.conn.commit()

    def siparisi_onayla(self, adisyon_id):
        self.conn.execute(
            "UPDATE adisyon_kalemleri SET durum='onaylandi' WHERE adisyon_id=? AND durum='bekliyor'",
            (adisyon_id,),
        )
        self.conn.commit()

    def adisyon_toplami(self, adisyon_id):
        row = self.conn.execute(
            """SELECT COALESCE(SUM(birim_fiyat * adet), 0) AS toplam
               FROM adisyon_kalemleri WHERE adisyon_id=? AND durum != 'iptal'""",
            (adisyon_id,),
        ).fetchone()
        return row["toplam"]

    # -- ödeme -----------------------------------------------------------------
    def odenen_tutar(self, adisyon_id):
        row = self.conn.execute(
            "SELECT COALESCE(SUM(tutar), 0) AS t FROM odemeler WHERE adisyon_id=?",
            (adisyon_id,),
        ).fetchone()
        return row["t"]

    def odeme_al(self, adisyon_id, yontem, tutar):
        self.conn.execute(
            "INSERT INTO odemeler (adisyon_id, yontem, tutar, zaman) VALUES (?, ?, ?, ?)",
            (adisyon_id, yontem, tutar, self._simdi()),
        )
        self.conn.commit()
        toplam = self.adisyon_toplami(adisyon_id)
        odenen = self.odenen_tutar(adisyon_id)
        if odenen >= toplam - 0.0001:
            self.adisyonu_kapat(adisyon_id)
            return True
        return False

    def adisyonu_kapat(self, adisyon_id):
        row = self.conn.execute(
            "SELECT masa_id FROM adisyonlar WHERE id=?", (adisyon_id,)
        ).fetchone()
        self.conn.execute(
            "UPDATE adisyonlar SET durum='kapali', kapanis_zamani=? WHERE id=?",
            (self._simdi(), adisyon_id),
        )
        if row:
            self.masa_durum_guncelle(row["masa_id"], "bos")
        self.conn.commit()

    def odemeleri_getir(self, adisyon_id):
        return self.conn.execute(
            "SELECT * FROM odemeler WHERE adisyon_id=? ORDER BY id", (adisyon_id,)
        ).fetchall()

    # -- muhasebe ----------------------------------------------------------
    def satis_raporu(self, baslangic, bitis):
        """baslangic/bitis: 'YYYY-MM-DD' formatında (dahil)."""
        satirlar = self.conn.execute(
            """SELECT yontem, COALESCE(SUM(tutar),0) AS toplam, COUNT(*) AS adet
               FROM odemeler
               WHERE date(zaman) BETWEEN date(?) AND date(?)
               GROUP BY yontem""",
            (baslangic, bitis),
        ).fetchall()
        genel_toplam = self.conn.execute(
            """SELECT COALESCE(SUM(tutar),0) AS t FROM odemeler
               WHERE date(zaman) BETWEEN date(?) AND date(?)""",
            (baslangic, bitis),
        ).fetchone()["t"]
        return satirlar, genel_toplam

    def gunluk_satis_dokumu(self, baslangic, bitis):
        return self.conn.execute(
            """SELECT date(zaman) AS gun, COALESCE(SUM(tutar),0) AS toplam
               FROM odemeler
               WHERE date(zaman) BETWEEN date(?) AND date(?)
               GROUP BY date(zaman) ORDER BY gun DESC""",
            (baslangic, bitis),
        ).fetchall()

    def gider_ekle(self, aciklama, tutar, tarih):
        self.conn.execute(
            "INSERT INTO giderler (aciklama, tutar, tarih) VALUES (?, ?, ?)",
            (aciklama, tutar, tarih),
        )
        self.conn.commit()

    def giderleri_getir(self, baslangic, bitis):
        return self.conn.execute(
            """SELECT * FROM giderler WHERE date(tarih) BETWEEN date(?) AND date(?)
               ORDER BY tarih DESC""",
            (baslangic, bitis),
        ).fetchall()

    def gider_toplami(self, baslangic, bitis):
        row = self.conn.execute(
            """SELECT COALESCE(SUM(tutar),0) AS t FROM giderler
               WHERE date(tarih) BETWEEN date(?) AND date(?)""",
            (baslangic, bitis),
        ).fetchone()
        return row["t"]

    def gider_sil(self, gider_id):
        self.conn.execute("DELETE FROM giderler WHERE id=?", (gider_id,))
        self.conn.commit()


# ---------------------------------------------------------------------------
# YARDIMCI ARAYÜZ FONKSİYONLARI
# ---------------------------------------------------------------------------
def tl(tutar):
    return f"{tutar:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")


def bugun():
    return datetime.date.today().strftime("%Y-%m-%d")


def ay_basi():
    return datetime.date.today().replace(day=1).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# MASA SİPARİŞ / ÖDEME PENCERESİ
# ---------------------------------------------------------------------------
class MasaPenceresi(tk.Toplevel):
    def __init__(self, master, db: VeriTabani, masa, yenile_callback):
        super().__init__(master)
        self.db = db
        self.masa = masa
        self.yenile_callback = yenile_callback
        self.title(f"{masa['ad']} - Sipariş")
        self.geometry("880x560")
        self.minsize(760, 480)

        self.adisyon_id = self.db.masa_ac(masa["id"])

        self._arayuz_kur()
        self._urunleri_yukle()
        self._siparisi_yenile()

        self.protocol("WM_DELETE_WINDOW", self._kapat)

    # -- arayüz --------------------------------------------------------
    def _arayuz_kur(self):
        ana = ttk.Frame(self, padding=10)
        ana.pack(fill="both", expand=True)
        ana.columnconfigure(0, weight=1)
        ana.columnconfigure(1, weight=1)
        ana.rowconfigure(0, weight=1)

        # Sol taraf: ürün seçimi
        sol = ttk.LabelFrame(ana, text="Menü - Sipariş Ekle", padding=8)
        sol.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        sol.rowconfigure(0, weight=1)
        sol.columnconfigure(0, weight=1)

        self.urun_listesi = ttk.Treeview(
            sol, columns=("kategori", "fiyat"), show="tree headings", height=14
        )
        self.urun_listesi.heading("#0", text="Ürün")
        self.urun_listesi.heading("kategori", text="Kategori")
        self.urun_listesi.heading("fiyat", text="Fiyat")
        self.urun_listesi.column("#0", width=180)
        self.urun_listesi.column("kategori", width=100)
        self.urun_listesi.column("fiyat", width=90, anchor="e")
        self.urun_listesi.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.urun_listesi.bind("<Double-1>", lambda e: self._siparise_ekle())

        ttk.Label(sol, text="Adet:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.adet_var = tk.IntVar(value=1)
        ttk.Spinbox(sol, from_=1, to=99, textvariable=self.adet_var, width=6).grid(
            row=1, column=1, sticky="w", pady=(8, 0)
        )
        ttk.Button(sol, text="Siparişe Ekle ➜", command=self._siparise_ekle).grid(
            row=1, column=2, sticky="e", pady=(8, 0)
        )

        # Sağ taraf: mevcut sipariş
        sag = ttk.LabelFrame(ana, text=f"{self.masa['ad']} Adisyonu", padding=8)
        sag.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        sag.rowconfigure(0, weight=1)
        sag.columnconfigure(0, weight=1)

        self.siparis_listesi = ttk.Treeview(
            sag,
            columns=("adet", "birim", "tutar", "durum"),
            show="tree headings",
            height=14,
        )
        self.siparis_listesi.heading("#0", text="Ürün")
        self.siparis_listesi.heading("adet", text="Adet")
        self.siparis_listesi.heading("birim", text="Birim")
        self.siparis_listesi.heading("tutar", text="Tutar")
        self.siparis_listesi.heading("durum", text="Durum")
        self.siparis_listesi.column("#0", width=160)
        self.siparis_listesi.column("adet", width=50, anchor="center")
        self.siparis_listesi.column("birim", width=80, anchor="e")
        self.siparis_listesi.column("tutar", width=80, anchor="e")
        self.siparis_listesi.column("durum", width=90, anchor="center")
        self.siparis_listesi.grid(row=0, column=0, columnspan=3, sticky="nsew")

        ttk.Button(sag, text="Seçileni Sil", command=self._kalem_sil).grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Button(sag, text="Siparişi Onayla", command=self._onayla).grid(
            row=1, column=1, sticky="ew", pady=(8, 0)
        )

        self.toplam_label = ttk.Label(sag, text="Toplam: 0,00 ₺", font=("Segoe UI", 12, "bold"))
        self.toplam_label.grid(row=2, column=0, columnspan=3, sticky="e", pady=(10, 0))

        alt = ttk.Frame(ana)
        alt.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        alt.columnconfigure(0, weight=1)
        ttk.Button(alt, text="Öde / Kapat", command=self._odeme_penceresi_ac).pack(
            side="right"
        )

    def _urunleri_yukle(self):
        self.urun_listesi.delete(*self.urun_listesi.get_children())
        self._urun_map = {}
        for u in self.db.urunleri_getir():
            iid = self.urun_listesi.insert(
                "", "end", text=u["ad"], values=(u["kategori"], tl(u["fiyat"]))
            )
            self._urun_map[iid] = u

    # -- eylemler --------------------------------------------------------
    def _siparise_ekle(self):
        sec = self.urun_listesi.selection()
        if not sec:
            messagebox.showinfo("Bilgi", "Lütfen bir ürün seçin.", parent=self)
            return
        urun = self._urun_map[sec[0]]
        adet = self.adet_var.get()
        if adet <= 0:
            messagebox.showwarning("Uyarı", "Adet 1 veya daha büyük olmalı.", parent=self)
            return
        self.db.siparis_ekle(self.adisyon_id, urun["id"], urun["ad"], urun["fiyat"], adet)
        self._siparisi_yenile()

    def _secili_kalem_id(self):
        sec = self.siparis_listesi.selection()
        if not sec:
            return None
        return self._kalem_map.get(sec[0])

    def _kalem_sil(self):
        kalem_id = self._secili_kalem_id()
        if kalem_id is None:
            messagebox.showinfo("Bilgi", "Silmek için bir sipariş satırı seçin.", parent=self)
            return
        self.db.kalem_sil(kalem_id)
        self._siparisi_yenile()

    def _onayla(self):
        self.db.siparisi_onayla(self.adisyon_id)
        self._siparisi_yenile()
        messagebox.showinfo("Onaylandı", "Bekleyen kalemler onaylandı.", parent=self)

    def _siparisi_yenile(self):
        self.siparis_listesi.delete(*self.siparis_listesi.get_children())
        self._kalem_map = {}
        for k in self.db.siparis_kalemleri_getir(self.adisyon_id):
            tutar = k["birim_fiyat"] * k["adet"]
            durum_metin = "Onaylı" if k["durum"] == "onaylandi" else "Bekliyor"
            iid = self.siparis_listesi.insert(
                "",
                "end",
                text=k["urun_adi"],
                values=(k["adet"], tl(k["birim_fiyat"]), tl(tutar), durum_metin),
            )
            self._kalem_map[iid] = k["id"]
        toplam = self.db.adisyon_toplami(self.adisyon_id)
        self.toplam_label.config(text=f"Toplam: {tl(toplam)}")

    def _odeme_penceresi_ac(self):
        toplam = self.db.adisyon_toplami(self.adisyon_id)
        if toplam <= 0:
            messagebox.showinfo("Bilgi", "Adisyonda kalem yok, ödeme alınamaz.", parent=self)
            return
        OdemePenceresi(self, self.db, self.adisyon_id, toplam, self._odeme_tamam)

    def _odeme_tamam(self):
        self._siparisi_yenile()
        self.yenile_callback()
        odenen = self.db.odenen_tutar(self.adisyon_id)
        toplam = self.db.adisyon_toplami(self.adisyon_id)
        if odenen >= toplam - 0.0001:
            messagebox.showinfo("Ödeme Alındı", f"{self.masa['ad']} kapatıldı.", parent=self)
            self.destroy()

    def _kapat(self):
        self.yenile_callback()
        self.destroy()


class OdemePenceresi(tk.Toplevel):
    def __init__(self, master, db: VeriTabani, adisyon_id, toplam, tamamlandi_callback):
        super().__init__(master)
        self.db = db
        self.adisyon_id = adisyon_id
        self.tamamlandi_callback = tamamlandi_callback
        self.title("Ödeme Al")
        self.geometry("360x260")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        kalan = toplam - db.odenen_tutar(adisyon_id)

        frm = ttk.Frame(self, padding=14)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text=f"Toplam Tutar: {tl(toplam)}").pack(anchor="w")
        self.kalan_label = ttk.Label(
            frm, text=f"Kalan: {tl(kalan)}", font=("Segoe UI", 10, "bold")
        )
        self.kalan_label.pack(anchor="w", pady=(0, 10))

        ttk.Label(frm, text="Ödeme Yöntemi:").pack(anchor="w")
        self.yontem_var = tk.StringVar(value=ODEME_YONTEMLERI[0])
        ttk.Combobox(
            frm, textvariable=self.yontem_var, values=ODEME_YONTEMLERI, state="readonly"
        ).pack(fill="x", pady=(0, 10))

        ttk.Label(frm, text="Tutar:").pack(anchor="w")
        self.tutar_var = tk.StringVar(value=f"{kalan:.2f}")
        ttk.Entry(frm, textvariable=self.tutar_var).pack(fill="x", pady=(0, 14))

        btns = ttk.Frame(frm)
        btns.pack(fill="x")
        ttk.Button(btns, text="Ödemeyi Uygula", command=self._odeme_uygula).pack(
            side="left", expand=True, fill="x"
        )
        ttk.Button(btns, text="Vazgeç", command=self.destroy).pack(
            side="left", expand=True, fill="x", padx=(6, 0)
        )

        self._toplam = toplam

    def _odeme_uygula(self):
        try:
            tutar = float(self.tutar_var.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Hata", "Geçerli bir tutar girin.", parent=self)
            return
        if tutar <= 0:
            messagebox.showerror("Hata", "Tutar 0'dan büyük olmalı.", parent=self)
            return
        kapandi = self.db.odeme_al(self.adisyon_id, self.yontem_var.get(), tutar)
        self.tamamlandi_callback()
        if kapandi:
            self.destroy()
        else:
            kalan = self._toplam - self.db.odenen_tutar(self.adisyon_id)
            self.kalan_label.config(text=f"Kalan: {tl(kalan)}")
            self.tutar_var.set(f"{kalan:.2f}")
            messagebox.showinfo(
                "Kısmi Ödeme", f"Ödeme kaydedildi. Kalan: {tl(kalan)}", parent=self
            )


# ---------------------------------------------------------------------------
# ANA PENCERE - SEKMELER
# ---------------------------------------------------------------------------
class AdisyonUygulamasi(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Adisyon Sistemi")
        self.geometry("1000x680")
        self.minsize(860, 560)

        self.db = VeriTabani()

        self._stil_ayarla()
        self._notebook_kur()

    def _stil_ayarla(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Bos.TButton", background="#2ecc71", foreground="white")
        style.configure("Dolu.TButton", background="#e74c3c", foreground="white")

    def _notebook_kur(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.masalar_sekmesi = MasalarSekmesi(self.notebook, self.db)
        self.urunler_sekmesi = UrunlerSekmesi(self.notebook, self.db)
        self.muhasebe_sekmesi = MuhasebeSekmesi(self.notebook, self.db)

        self.notebook.add(self.masalar_sekmesi, text="Masalar")
        self.notebook.add(self.urunler_sekmesi, text="Ürün Yönetimi")
        self.notebook.add(self.muhasebe_sekmesi, text="Muhasebe")

        self.notebook.bind("<<NotebookTabChanged>>", self._sekme_degisti)

    def _sekme_degisti(self, event):
        secili = self.notebook.select()
        if secili == str(self.muhasebe_sekmesi):
            self.muhasebe_sekmesi.yenile()
        elif secili == str(self.urunler_sekmesi):
            self.urunler_sekmesi.yenile()
        elif secili == str(self.masalar_sekmesi):
            self.masalar_sekmesi.yenile()


# ---------------------------------------------------------------------------
# SEKME: MASALAR
# ---------------------------------------------------------------------------
class MasalarSekmesi(ttk.Frame):
    def __init__(self, master, db: VeriTabani):
        super().__init__(master, padding=12)
        self.db = db
        self._arayuz_kur()
        self.yenile()

    def _arayuz_kur(self):
        ust = ttk.Frame(self)
        ust.pack(fill="x", pady=(0, 10))
        ttk.Button(ust, text="+ Yeni Masa Ekle", command=self._masa_ekle).pack(side="left")
        ttk.Button(ust, text="Seçili Masayı Sil", command=self._masa_sil_iste).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(ust, text="Yenile", command=self.yenile).pack(side="right")

        self.grid_alani = ttk.Frame(self)
        self.grid_alani.pack(fill="both", expand=True)

        self._secili_masa_id = None

    def _masa_ekle(self):
        ad = simpledialog.askstring("Yeni Masa", "Masa adı:", parent=self)
        if ad:
            self.db.masa_ekle(ad)
            self.yenile()

    def _masa_sil_iste(self):
        if self._secili_masa_id is None:
            messagebox.showinfo("Bilgi", "Silmek için önce bir masaya sağ tıklayın.", parent=self)
            return
        try:
            self.db.masa_sil(self._secili_masa_id)
        except ValueError as e:
            messagebox.showerror("Hata", str(e), parent=self)
        self.yenile()

    def _masa_sec(self, masa_id):
        self._secili_masa_id = masa_id

    def _masa_ac(self, masa):
        MasaPenceresi(self, self.db, masa, self.yenile)

    def yenile(self):
        for w in self.grid_alani.winfo_children():
            w.destroy()
        masalar = self.db.masalari_getir()
        kolon_sayisi = 4
        for idx, masa in enumerate(masalar):
            satir, kolon = divmod(idx, kolon_sayisi)
            stil = "Dolu.TButton" if masa["durum"] == "dolu" else "Bos.TButton"
            durum_metin = "DOLU" if masa["durum"] == "dolu" else "BOŞ"
            btn = ttk.Button(
                self.grid_alani,
                text=f"{masa['ad']}\n({durum_metin})",
                style=stil,
                command=lambda m=masa: self._masa_ac(m),
            )
            btn.grid(row=satir, column=kolon, padx=8, pady=8, ipadx=10, ipady=18, sticky="nsew")
            btn.bind("<Button-3>", lambda e, m=masa: self._masa_sec(m["id"]))
            self.grid_alani.columnconfigure(kolon, weight=1)


# ---------------------------------------------------------------------------
# SEKME: ÜRÜN YÖNETİMİ
# ---------------------------------------------------------------------------
class UrunlerSekmesi(ttk.Frame):
    def __init__(self, master, db: VeriTabani):
        super().__init__(master, padding=12)
        self.db = db
        self._arayuz_kur()
        self.yenile()

    def _arayuz_kur(self):
        form = ttk.LabelFrame(self, text="Ürün Ekle / Güncelle", padding=10)
        form.pack(fill="x", pady=(0, 10))

        ttk.Label(form, text="Ad:").grid(row=0, column=0, sticky="w")
        self.ad_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.ad_var, width=24).grid(row=0, column=1, padx=6)

        ttk.Label(form, text="Kategori:").grid(row=0, column=2, sticky="w")
        self.kategori_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.kategori_var, width=16).grid(row=0, column=3, padx=6)

        ttk.Label(form, text="Fiyat:").grid(row=0, column=4, sticky="w")
        self.fiyat_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.fiyat_var, width=10).grid(row=0, column=5, padx=6)

        ttk.Button(form, text="Ekle", command=self._urun_ekle).grid(row=0, column=6, padx=(10, 0))
        ttk.Button(form, text="Güncelle", command=self._urun_guncelle).grid(row=0, column=7, padx=4)

        self.liste = ttk.Treeview(
            self, columns=("kategori", "fiyat"), show="tree headings", height=16
        )
        self.liste.heading("#0", text="Ürün")
        self.liste.heading("kategori", text="Kategori")
        self.liste.heading("fiyat", text="Fiyat")
        self.liste.pack(fill="both", expand=True)
        self.liste.bind("<<TreeviewSelect>>", self._secim_degisti)

        alt = ttk.Frame(self)
        alt.pack(fill="x", pady=(8, 0))
        ttk.Button(alt, text="Seçileni Pasifleştir / Sil", command=self._urun_sil).pack(
            side="left"
        )

        self._urun_map = {}
        self._secili_id = None

    def _secim_degisti(self, event):
        sec = self.liste.selection()
        if not sec:
            return
        urun = self._urun_map[sec[0]]
        self._secili_id = urun["id"]
        self.ad_var.set(urun["ad"])
        self.kategori_var.set(urun["kategori"])
        self.fiyat_var.set(str(urun["fiyat"]))

    def _fiyat_oku(self):
        try:
            return float(self.fiyat_var.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Hata", "Geçerli bir fiyat girin.", parent=self)
            return None

    def _urun_ekle(self):
        ad = self.ad_var.get().strip()
        kategori = self.kategori_var.get().strip() or "Genel"
        fiyat = self._fiyat_oku()
        if not ad or fiyat is None:
            messagebox.showwarning("Uyarı", "Ürün adı ve fiyat gerekli.", parent=self)
            return
        self.db.urun_ekle(ad, kategori, fiyat)
        self._formu_temizle()
        self.yenile()

    def _urun_guncelle(self):
        if self._secili_id is None:
            messagebox.showinfo("Bilgi", "Önce listeden bir ürün seçin.", parent=self)
            return
        ad = self.ad_var.get().strip()
        kategori = self.kategori_var.get().strip() or "Genel"
        fiyat = self._fiyat_oku()
        if not ad or fiyat is None:
            return
        self.db.urun_guncelle(self._secili_id, ad, kategori, fiyat)
        self._formu_temizle()
        self.yenile()

    def _urun_sil(self):
        if self._secili_id is None:
            messagebox.showinfo("Bilgi", "Önce listeden bir ürün seçin.", parent=self)
            return
        self.db.urun_sil(self._secili_id)
        self._formu_temizle()
        self.yenile()

    def _formu_temizle(self):
        self._secili_id = None
        self.ad_var.set("")
        self.kategori_var.set("")
        self.fiyat_var.set("")

    def yenile(self):
        self.liste.delete(*self.liste.get_children())
        self._urun_map = {}
        for u in self.db.urunleri_getir():
            iid = self.liste.insert("", "end", text=u["ad"], values=(u["kategori"], tl(u["fiyat"])))
            self._urun_map[iid] = u


# ---------------------------------------------------------------------------
# SEKME: MUHASEBE
# ---------------------------------------------------------------------------
class MuhasebeSekmesi(ttk.Frame):
    def __init__(self, master, db: VeriTabani):
        super().__init__(master, padding=12)
        self.db = db
        self._arayuz_kur()
        self.yenile()

    def _arayuz_kur(self):
        ust = ttk.LabelFrame(self, text="Tarih Aralığı", padding=10)
        ust.pack(fill="x", pady=(0, 10))

        ttk.Label(ust, text="Başlangıç (YYYY-AA-GG):").grid(row=0, column=0, sticky="w")
        self.baslangic_var = tk.StringVar(value=ay_basi())
        ttk.Entry(ust, textvariable=self.baslangic_var, width=12).grid(row=0, column=1, padx=6)

        ttk.Label(ust, text="Bitiş (YYYY-AA-GG):").grid(row=0, column=2, sticky="w")
        self.bitis_var = tk.StringVar(value=bugun())
        ttk.Entry(ust, textvariable=self.bitis_var, width=12).grid(row=0, column=3, padx=6)

        ttk.Button(ust, text="Raporu Göster", command=self.yenile).grid(row=0, column=4, padx=10)

        gövde = ttk.Frame(self)
        gövde.pack(fill="both", expand=True)
        gövde.columnconfigure(0, weight=1)
        gövde.columnconfigure(1, weight=1)
        gövde.rowconfigure(0, weight=1)

        # Sol: ödeme yöntemine göre satış + özet
        sol = ttk.LabelFrame(gövde, text="Satış Özeti", padding=10)
        sol.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.yontem_liste = ttk.Treeview(
            sol, columns=("adet", "toplam"), show="headings", height=6
        )
        self.yontem_liste.heading("adet", text="İşlem Adedi")
        self.yontem_liste.heading("toplam", text="Toplam")
        self.yontem_liste.pack(fill="x")

        self.ozet_label = ttk.Label(sol, text="", font=("Segoe UI", 10, "bold"), justify="left")
        self.ozet_label.pack(anchor="w", pady=(10, 0))

        ttk.Label(sol, text="Günlük Satış Dökümü:").pack(anchor="w", pady=(14, 0))
        self.gunluk_liste = ttk.Treeview(sol, columns=("toplam",), show="headings", height=8)
        self.gunluk_liste.heading("toplam", text="Toplam")
        self.gunluk_liste["columns"] = ("gun", "toplam")
        self.gunluk_liste.heading("gun", text="Tarih")
        self.gunluk_liste.heading("toplam", text="Toplam")
        self.gunluk_liste.pack(fill="both", expand=True, pady=(4, 0))

        # Sağ: giderler
        sag = ttk.LabelFrame(gövde, text="Giderler", padding=10)
        sag.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        form = ttk.Frame(sag)
        form.pack(fill="x")
        ttk.Label(form, text="Açıklama:").grid(row=0, column=0, sticky="w")
        self.gider_aciklama_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.gider_aciklama_var, width=18).grid(row=0, column=1, padx=4)
        ttk.Label(form, text="Tutar:").grid(row=0, column=2, sticky="w")
        self.gider_tutar_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.gider_tutar_var, width=10).grid(row=0, column=3, padx=4)
        ttk.Label(form, text="Tarih:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.gider_tarih_var = tk.StringVar(value=bugun())
        ttk.Entry(form, textvariable=self.gider_tarih_var, width=12).grid(
            row=1, column=1, padx=4, pady=(4, 0), sticky="w"
        )
        ttk.Button(form, text="Gider Ekle", command=self._gider_ekle).grid(
            row=1, column=2, columnspan=2, sticky="e", pady=(4, 0)
        )

        self.gider_liste = ttk.Treeview(
            sag, columns=("tutar", "tarih"), show="headings", height=10
        )
        self.gider_liste["columns"] = ("aciklama", "tutar", "tarih")
        self.gider_liste.heading("aciklama", text="Açıklama")
        self.gider_liste.heading("tutar", text="Tutar")
        self.gider_liste.heading("tarih", text="Tarih")
        self.gider_liste.pack(fill="both", expand=True, pady=(10, 0))

        ttk.Button(sag, text="Seçili Gideri Sil", command=self._gider_sil).pack(
            anchor="e", pady=(6, 0)
        )

        self._gider_map = {}

    def _gider_ekle(self):
        aciklama = self.gider_aciklama_var.get().strip()
        try:
            tutar = float(self.gider_tutar_var.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Hata", "Geçerli bir tutar girin.", parent=self)
            return
        tarih = self.gider_tarih_var.get().strip() or bugun()
        if not aciklama:
            messagebox.showwarning("Uyarı", "Açıklama girin.", parent=self)
            return
        self.db.gider_ekle(aciklama, tutar, tarih)
        self.gider_aciklama_var.set("")
        self.gider_tutar_var.set("")
        self.yenile()

    def _gider_sil(self):
        sec = self.gider_liste.selection()
        if not sec:
            return
        gider_id = self._gider_map.get(sec[0])
        if gider_id is not None:
            self.db.gider_sil(gider_id)
            self.yenile()

    def yenile(self):
        b = self.baslangic_var.get().strip()
        s = self.bitis_var.get().strip()
        try:
            satirlar, genel_toplam = self.db.satis_raporu(b, s)
        except sqlite3.OperationalError:
            messagebox.showerror("Hata", "Tarih formatı YYYY-AA-GG olmalı.", parent=self)
            return

        self.yontem_liste.delete(*self.yontem_liste.get_children())
        for row in satirlar:
            self.yontem_liste.insert(
                "", "end", text=row["yontem"], values=(row["adet"], tl(row["toplam"]))
            )
        # show="headings" olduğundan text görünmez; ayrı bir sütun olarak ekleyelim
        self.yontem_liste["columns"] = ("yontem", "adet", "toplam")
        self.yontem_liste.heading("yontem", text="Yöntem")
        self.yontem_liste.delete(*self.yontem_liste.get_children())
        for row in satirlar:
            self.yontem_liste.insert(
                "", "end", values=(row["yontem"], row["adet"], tl(row["toplam"]))
            )

        gider_toplam = self.db.gider_toplami(b, s)
        net = genel_toplam - gider_toplam
        self.ozet_label.config(
            text=(
                f"Toplam Satış: {tl(genel_toplam)}\n"
                f"Toplam Gider: {tl(gider_toplam)}\n"
                f"Net Kâr: {tl(net)}"
            )
        )

        self.gunluk_liste.delete(*self.gunluk_liste.get_children())
        for g in self.db.gunluk_satis_dokumu(b, s):
            self.gunluk_liste.insert("", "end", values=(g["gun"], tl(g["toplam"])))

        self.gider_liste.delete(*self.gider_liste.get_children())
        self._gider_map = {}
        for g in self.db.giderleri_getir(b, s):
            iid = self.gider_liste.insert(
                "", "end", values=(g["aciklama"], tl(g["tutar"]), g["tarih"])
            )
            self._gider_map[iid] = g["id"]


# ---------------------------------------------------------------------------
# BAŞLAT
# ---------------------------------------------------------------------------
def main():
    app = AdisyonUygulamasi()
    app.mainloop()


if __name__ == "__main__":
    main()
