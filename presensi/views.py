import pandas as pd
import openpyxl
from django.core.signing import Signer
from django.contrib import messages
from django.db import models
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import OPD, Presensi, DMSPegawai, LandingPageSetting
from django.utils import timezone

signer = Signer()  # Inisialisasi pengaman / enkripsi URL


def admin_login_view(request):
    if request.user.is_authenticated:
        return redirect("admin_dashboard")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Selamat datang kembali, {username}!")
                return redirect("admin_dashboard")
        else:
            messages.error(request, "Username atau password salah.")
    else:
        form = AuthenticationForm()

    return render(request, "presensi/login.html", {"form": form})


@login_required(login_url="admin_login")
def dashboard_admin_view(request):
    total_opd = OPD.objects.count()
    total_presensi = Presensi.objects.count()
    recent_presensi = Presensi.objects.select_related("opd").order_by(
        "-waktu_submit"
    )[:10]

    context = {
        "total_opd": total_opd,
        "total_presensi": total_presensi,
        "recent_presensi": recent_presensi,
        "user": request.user,
    }
    return render(request, "presensi/dashboard.html", context)


def logout_view(request):
    logout(request)
    messages.success(request, "Anda berhasil logout.")
    return redirect("admin_login")


@login_required(login_url="admin_login")
def kelola_opd_view(request):
    opd_list = OPD.objects.all().order_by("nama_opd")
    return render(request, "presensi/kelola_opd.html", {"opd_list": opd_list})


@login_required(login_url="admin_login")
def tambah_opd_view(request):
    if request.method == "POST":
        nama_opd = request.POST.get("nama_opd")
        singkatan = request.POST.get("singkatan")
        if nama_opd:
            try:
                OPD.objects.create(nama_opd=nama_opd, singkatan=singkatan)
                messages.success(request, "Data OPD berhasil ditambahkan!")
            except Exception:
                messages.error(
                    request,
                    "Gagal menambahkan OPD. Kemungkinan nama OPD sudah terdaftar.",
                )
    return redirect("kelola_opd")


@login_required(login_url="admin_login")
def edit_opd_view(request, opd_id):
    opd = get_object_or_404(OPD, id=opd_id)
    if request.method == "POST":
        nama_opd = request.POST.get("nama_opd")
        singkatan = request.POST.get("singkatan")
        if nama_opd:
            opd.nama_opd = nama_opd
            opd.singkatan = singkatan
            opd.save()
            messages.success(request, "Data OPD berhasil diperbarui!")
    return redirect("kelola_opd")


@login_required(login_url="admin_login")
def hapus_opd_view(request, opd_id):
    opd = get_object_or_404(OPD, id=opd_id)
    opd.delete()
    messages.success(request, "Data OPD berhasil dihapus!")
    return redirect("kelola_opd")


@login_required(login_url="admin_login")
def import_opd_excel_view(request):
    if request.method == "POST":
        excel_file = request.FILES.get("file_excel")

        if not excel_file:
            messages.error(request, "Pilih file Excel terlebih dahulu!")
            return redirect("kelola_opd")

        if not excel_file.name.endswith((".xls", ".xlsx")):
            messages.error(request, "Format file harus .xls atau .xlsx")
            return redirect("kelola_opd")

        try:
            df = pd.read_excel(excel_file)

            if (
                "nama_opd" not in df.columns
                and "Nama OPD" not in df.columns
                and "OPD" not in df.columns
            ):
                messages.error(
                    request,
                    "Format kolom Excel tidak dikenali. Pastikan ada kolom dengan judul 'nama_opd' atau 'Nama OPD'.",
                )
                return redirect("kelola_opd")

            df.columns = [str(col).strip().lower() for col in df.columns]

            kolom_nama = (
                "nama_opd"
                if "nama_opd" in df.columns
                else ("opd" if "opd" in df.columns else "nama opd")
            )
            kolom_singkatan = (
                "singkatan" if "singkatan" in df.columns else None
            )

            success_count = 0
            duplicate_count = 0

            for _, row in df.iterrows():
                nama_opd = str(row[kolom_nama]).strip()
                if not nama_opd or nama_opd.lower() == "nan":
                    continue

                singkatan = None
                if kolom_singkatan and row[kolom_singkatan]:
                    val_singkatan = str(row[kolom_singkatan]).strip()
                    if val_singkatan.lower() != "nan":
                        singkatan = val_singkatan

                _, created = OPD.objects.get_or_create(
                    nama_opd=nama_opd, defaults={"singkatan": singkatan}
                )

                if created:
                    success_count += 1
                else:
                    duplicate_count += 1

            messages.success(
                request,
                f"Berhasil mengimpor {success_count} OPD baru. {duplicate_count} data dilewati karena sudah ada.",
            )

        except Exception as e:
            messages.error(request, f"Terjadi kesalahan saat membaca file: {e}")

    return redirect("kelola_opd")


# ==========================================
# FITUR PRESENSI PUBLIK GLOBAL & AJAX SUBMIT
# ==========================================


def form_presensi_global_view(request):
    setting = LandingPageSetting.objects.filter(is_active=True).first()
    
    presensi_aktif, status_text = (True, "Buka")
    if setting:
        presensi_aktif, status_text = setting.is_presensi_open()

    # Tetap muat data OPD dan render template form_presensi_global.html
    # agar modal popup & countdown di HTML bisa dirender oleh browser
    opd_list = OPD.objects.all().order_by("nama_opd")
    
    context = {
        "setting": setting,
        "opd_list": opd_list,
        "presensi_aktif": presensi_aktif,
        "status_text": status_text,
    }
    return render(request, "presensi/form_presensi_global.html", context)


@require_POST
def submit_presensi_global_api(request):
    opd_id = request.POST.get("opd_id")
    nama = request.POST.get("nama")
    nip = request.POST.get("nip")
    jabatan = request.POST.get("jabatan")

    if not opd_id or not nama or not nip:
        return JsonResponse(
            {"status": "error", "message": "OPD, Nama, dan NIP wajib diisi!"},
            status=400,
        )

    opd_pilih = get_object_or_404(OPD, id=opd_id)
    presensi_sebelumnya = Presensi.objects.filter(nip=nip).first()
    
    if presensi_sebelumnya:
        opd_asal_id = presensi_sebelumnya.opd.id
        nama_opd_asal = presensi_sebelumnya.opd.nama_opd
        encrypted_id = signer.sign(str(opd_asal_id))
        
        return JsonResponse(
            {
                "status": "already_exists",
                "message": f"NIP tersebut sudah tercatat melakukan presensi sebelumnya di {nama_opd_asal}. Anda akan diarahkan ke halaman rekap.",
                "token_id": encrypted_id,
            },
            status=400,
        )

    try:
        Presensi.objects.create(
            opd=opd_pilih, nama=nama, nip=nip, jabatan=jabatan if jabatan else ""
        )
        encrypted_id = signer.sign(str(opd_pilih.id))
        
        return JsonResponse(
            {
                "status": "success",
                "message": "Presensi berhasil direkam. Terima kasih!",
                "token_id": encrypted_id,
            }
        )
    except Exception as e:
        return JsonResponse(
            {"status": "error", "message": f"Terjadi kesalahan sistem: {e}"},
            status=500,
        )


def hasil_presensi_opd_view(request, token_id):
    try:
        opd_id = signer.unsign(token_id)
    except Exception:
        raise Http404("Halaman tidak ditemukan.")

    opd = get_object_or_404(OPD, id=opd_id)
    
    if not opd.nama_opd:
        pegawai_dms_list = DMSPegawai.objects.none()
    else:
        q_filter = models.Q(opd_induk__iexact=opd.nama_opd) | models.Q(opd_induk__icontains=opd.nama_opd)
        if opd.singkatan:
            q_filter |= models.Q(opd_induk__iexact=opd.singkatan) | models.Q(opd_induk__icontains=opd.singkatan)
            
        pegawai_dms_list = DMSPegawai.objects.filter(q_filter).order_by("nama")

    rekap_data = []
    for index, pegawai in enumerate(pegawai_dms_list, start=1):
        sudah_absen = Presensi.objects.filter(opd=opd, nip=pegawai.nip).exists()

        rekap_data.append({
            "no": index,
            "nip": pegawai.nip,
            "nama": pegawai.nama,
            "skor": pegawai.skor,
            "opd_induk": pegawai.opd_induk,
            "unit_kerja": pegawai.unit_kerja,
            "sudah_absen": sudah_absen,
        })

    context = {
        "opd": opd,
        "rekap_data": rekap_data,
        "token_id": token_id,
    }
    return render(request, "presensi/hasil_presensi_opd.html", context)


def export_rekap_excel(request, token_id):
    try:
        opd_id = signer.unsign(token_id)
    except Exception:
        raise Http404("Halaman tidak ditemukan.")

    opd = get_object_or_404(OPD, id=opd_id)
    
    if not opd.nama_opd:
        pegawai_dms_list = DMSPegawai.objects.none()
    else:
        q_filter = models.Q(opd_induk__iexact=opd.nama_opd) | models.Q(opd_induk__icontains=opd.nama_opd)
        if opd.singkatan:
            q_filter |= models.Q(opd_induk__iexact=opd.singkatan) | models.Q(opd_induk__icontains=opd.singkatan)
            
        pegawai_dms_list = DMSPegawai.objects.filter(q_filter).order_by("nama")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rekap Presensi & DMS"

    ws.append([f"REKAP PRESENSI & SKOR DMS - {opd.nama_opd.upper()}"])
    ws.append([])

    headers = ["No", "NIP", "Nama Pegawai", "Skor", "OPD Induk", "Unit Kerja", "Status Kehadiran"]
    ws.append(headers)

    for index, pegawai in enumerate(pegawai_dms_list, start=1):
        sudah_absen = Presensi.objects.filter(opd=opd, nip=pegawai.nip).exists()
        status_kehadiran = "Hadir" if sudah_absen else "Belum Absen"

        ws.append([
            index,
            str(pegawai.nip),
            pegawai.nama,
            pegawai.skor,
            pegawai.opd_induk,
            pegawai.unit_kerja,
            status_kehadiran
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f"Rekap_Presensi_{opd.singkatan or 'OPD'}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    wb.save(response)
    return response


# ==========================================
# KELOLA PRESENSI DI ADMIN PANEL
# ==========================================


@login_required(login_url="admin_login")
def kelola_presensi_view(request):
    presensi_list = Presensi.objects.select_related("opd").order_by(
        "-waktu_submit"
    )
    return render(
        request, "presensi/kelola_presensi.html", {"presensi_list": presensi_list}
    )


@login_required(login_url="admin_login")
def hapus_presensi_view(request, presensi_id):
    presensi = get_object_or_404(Presensi, id=presensi_id)
    presensi.delete()
    messages.success(request, "Data presensi berhasil dihapus.")
    return redirect("kelola_presensi")


# ==========================================
# KELOLA DATA DMS PEGAWAI (ADMIN PANEL)
# ==========================================


@login_required(login_url="admin_login")
def kelola_dms_view(request):
    dms_list = DMSPegawai.objects.all().order_by("nama")
    context = {
        "dms_list": dms_list,
    }
    return render(request, "presensi/kelola_dms.html", context)


@login_required(login_url="admin_login")
def tambah_dms_view(request):
    if request.method == "POST":
        nip = request.POST.get("nip")
        nama = request.POST.get("nama")
        skor = request.POST.get("skor") or 0.0
        opd_induk = request.POST.get("opd_induk")
        unit_kerja = request.POST.get("unit_kerja")

        if nip and nama:
            try:
                DMSPegawai.objects.create(
                    nip=nip,
                    nama=nama,
                    skor=skor,
                    opd_induk=opd_induk,
                    unit_kerja=unit_kerja,
                )
                messages.success(request, "Data pegawai DMS berhasil ditambahkan!")
            except Exception as e:
                messages.error(
                    request, f"Gagal menambahkan data. Kemungkinan NIP sudah terdaftar: {e}"
                )
        else:
            messages.error(request, "NIP dan Nama wajib diisi!")
    return redirect("kelola_dms")


@login_required(login_url="admin_login")
def edit_dms_view(request, dms_id):
    pegawai = get_object_or_404(DMSPegawai, id=dms_id)
    if request.method == "POST":
        pegawai.nip = request.POST.get("nip")
        pegawai.nama = request.POST.get("nama")
        pegawai.skor = request.POST.get("skor") or 0.0
        pegawai.opd_induk = request.POST.get("opd_induk")
        pegawai.unit_kerja = request.POST.get("unit_kerja")
        pegawai.save()
        messages.success(request, "Data pegawai DMS berhasil diperbarui!")
    return redirect("kelola_dms")


@login_required(login_url="admin_login")
def hapus_dms_view(request, dms_id):
    pegawai = get_object_or_404(DMSPegawai, id=dms_id)
    pegawai.delete()
    messages.success(request, "Data pegawai DMS berhasil dihapus.")
    return redirect("kelola_dms")


@login_required(login_url="admin_login")
def import_dms_excel_view(request):
    if request.method == "POST":
        excel_file = request.FILES.get("file_excel")

        if not excel_file:
            messages.error(request, "Pilih file Excel terlebih dahulu!")
            return redirect("kelola_dms")

        if not excel_file.name.endswith((".xls", ".xlsx")):
            messages.error(request, "Format file harus .xls atau .xlsx")
            return redirect("kelola_dms")

        try:
            df = pd.read_excel(excel_file)
            df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]

            if "nip" not in df.columns or "nama" not in df.columns:
                messages.error(
                    request,
                    "Format kolom Excel tidak valid. Pastikan ada kolom 'nip' dan 'nama'.",
                )
                return redirect("kelola_dms")

            success_count = 0
            update_count = 0

            for _, row in df.iterrows():
                nip = str(row.get("nip", "")).strip()
                nama = str(row.get("nama", "")).strip()

                if not nip or nip.lower() == "nan" or not nama:
                    continue

                skor = row.get("skor", 0.0)
                try:
                    skor = float(skor)
                except ValueError:
                    skor = 0.0

                opd_induk = str(
                    row.get("opd_induk", row.get("opd", ""))
                ).strip()

                unit_kerja = str(
                    row.get(
                        "unit_kerja",
                        row.get("unit", row.get("satuan_kerja", row.get("jabatan", ""))),
                    )
                ).strip()

                obj, created = DMSPegawai.objects.update_or_create(
                    nip=nip,
                    defaults={
                        "nama": nama,
                        "skor": skor,
                        "opd_induk": opd_induk if opd_induk.lower() != "nan" else "",
                        "unit_kerja": unit_kerja if unit_kerja.lower() != "nan" else "",
                    },
                )

                if created:
                    success_count += 1
                else:
                    update_count += 1

            messages.success(
                request,
                f"Berhasil mengimpor {success_count} data baru dan memperbarui {update_count} data DMS.",
            )
        except Exception as e:
            messages.error(
                request, f"Terjadi kesalahan saat membaca file Excel: {e}"
            )

    return redirect("kelola_dms")


def landing_page_view(request):
    setting = LandingPageSetting.objects.filter(is_active=True).first()
    
    presensi_aktif, presensi_status_text = (True, "Buka")
    materi_aktif, materi_status_text = (True, "Buka")

    if setting:
        presensi_aktif, presensi_status_text = setting.is_presensi_open()
        materi_aktif, materi_status_text = setting.is_materi_open()

    context = {
        'setting': setting,
        'presensi_aktif': presensi_aktif,
        'presensi_status_text': presensi_status_text,
        'materi_aktif': materi_aktif,
        'materi_status_text': materi_status_text,
    }
    return render(request, "presensi/landing_page.html", context)


@login_required(login_url="admin_login")
def kelola_landing_list_view(request):
    settings_list = LandingPageSetting.objects.all().order_by('-created_at')
    return render(request, "presensi/kelola_landing_list.html", {"settings_list": settings_list})


@login_required(login_url="admin_login")
def kelola_landing_form_view(request, setting_id=None):
    setting = get_object_or_404(LandingPageSetting, id=setting_id) if setting_id else None

    if request.method == "POST":
        if not setting:
            setting = LandingPageSetting()

        setting.judul_acara = request.POST.get("judul_acara")
        setting.subjudul_acara = request.POST.get("subjudul_acara")
        setting.kode_sesi = request.POST.get("kode_sesi")
        setting.tagline_poster = request.POST.get("tagline_poster")
        setting.quote_poster = request.POST.get("quote_poster")
        
        setting.zoom_url = request.POST.get("zoom_url")
        setting.vb_url = request.POST.get("vb_url")
        setting.materi_url = request.POST.get("materi_url")

        setting.presensi_buka = request.POST.get("presensi_buka") or None
        setting.presensi_tutup = request.POST.get("presensi_tutup") or None
        setting.materi_buka = request.POST.get("materi_buka") or None
        setting.materi_tutup = request.POST.get("materi_tutup") or None

        if request.POST.get("is_active") == "on":
            LandingPageSetting.objects.update(is_active=False)
            setting.is_active = True
        else:
            if not LandingPageSetting.objects.filter(is_active=True).exists():
                setting.is_active = True

        if request.FILES.get("flyer_img"):
            setting.flyer_img = request.FILES.get("flyer_img")

        setting.save()
        messages.success(request, f"Pengaturan Event '{setting.judul_acara}' berhasil disimpan!")
        return redirect("kelola_landing")

    context = {"setting": setting}
    return render(request, "presensi/kelola_landing.html", context)


@login_required(login_url="admin_login")
def set_active_landing(request, setting_id):
    LandingPageSetting.objects.update(is_active=False)
    setting = get_object_or_404(LandingPageSetting, id=setting_id)
    setting.is_active = True
    setting.save()
    messages.success(request, f"Event '{setting.judul_acara}' sekarang diaktifkan di Landing Page Utama.")
    return redirect("kelola_landing")