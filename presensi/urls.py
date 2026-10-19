from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.admin_login_view, name="admin_login"),
    path("logout/", views.logout_view, name="admin_logout"),
    path("dashboard/", views.dashboard_admin_view, name="admin_dashboard"),
    # URL Kelola OPD
    path("dashboard/opd/", views.kelola_opd_view, name="kelola_opd"),
    path("dashboard/opd/tambah/", views.tambah_opd_view, name="tambah_opd"),
    path("dashboard/opd/edit/<int:opd_id>/", views.edit_opd_view, name="edit_opd"),
    path("dashboard/opd/hapus/<int:opd_id>/", views.hapus_opd_view, name="hapus_opd"),

    path("dashboard/opd/", views.kelola_opd_view, name="kelola_opd"),
    path("dashboard/opd/tambah/", views.tambah_opd_view, name="tambah_opd"),
    path("dashboard/opd/edit/<int:opd_id>/", views.edit_opd_view, name="edit_opd"),
    path("dashboard/opd/hapus/<int:opd_id>/", views.hapus_opd_view, name="hapus_opd"),
    path(
        "dashboard/opd/import/",
        views.import_opd_excel_view,
        name="import_opd_excel",
    ),  # <-- Tambahkan ini

    # Form Presensi Global & API (Tanpa Parameter OPD di URL)
    path("presensi/", views.form_presensi_global_view, name="form_presensi_global"),
    path("api/presensi/submit/", views.submit_presensi_global_api, name="submit_presensi_global_api"),
    
    # Halaman Publik Hasil Rekap / DMS per OPD setelah submit
    path("presensi/hasil/<str:token_id>/", views.hasil_presensi_opd_view, name="hasil_presensi_opd"),
    path("presensi/hasil/<str:token_id>/export/", views.export_rekap_excel, name="export_rekap_excel"),

    # Kelola Data Presensi (Admin Panel)
    path("presensi/kelola/", views.kelola_presensi_view, name="kelola_presensi"),
    path("presensi/hapus/<int:presensi_id>/", views.hapus_presensi_view, name="hapus_presensi"),

    # Kelola Data DMS Pegawai (Admin Panel)
    path("dms/", views.kelola_dms_view, name="kelola_dms"),
    path("dms/tambah/", views.tambah_dms_view, name="tambah_dms"),
    path("dms/edit/<int:dms_id>/", views.edit_dms_view, name="edit_dms"),
    path("dms/hapus/<int:dms_id>/", views.hapus_dms_view, name="hapus_dms"),
    path("dms/import/", views.import_dms_excel_view, name="import_dms_excel"),

    path("dashboard/landing/", views.kelola_landing_list_view, name="kelola_landing"),
    path("dashboard/landing/tambah/", views.kelola_landing_form_view, name="tambah_landing"),
    path("dashboard/landing/edit/<int:setting_id>/", views.kelola_landing_form_view, name="edit_landing"),
    path("dashboard/landing/activate/<int:setting_id>/", views.set_active_landing, name="set_active_landing"),
]