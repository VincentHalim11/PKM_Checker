import 'dart:async';
import 'dart:convert';
import 'dart:io';

/// Menjalankan engine Python (validator.py --json) dan mengembalikan hasilnya.
///
/// Lokasi engine dan Python TIDAK ditulis mutlak. Urutan pencarian:
///
/// MODE RILIS (aplikasi dibagikan ke pengguna lain):
///   Jika ada `engine/pkm_engine.exe` di samping .exe aplikasi, itulah yang
///   dijalankan (engine Python yang sudah dibungkus; pengguna tidak perlu
///   memasang Python). Dibuat oleh build_engine.ps1 + package_release.ps1.
///
/// MODE PENGEMBANGAN (jika engine terbungkus tidak ada):
///
/// Engine (folder `python_engine` yang berisi `src/validator.py`):
///   1. Environment variable `PKM_ENGINE_DIR`
///   2. Naik dari folder kerja saat ini, lalu dari folder .exe aplikasi;
///      di tiap tingkat dicek folder itu sendiri dan sub-folder `python_engine`.
///      (Cocok untuk `flutter run` maupun .exe yang diletakkan di samping
///      folder `python_engine`.)
///
/// Python:
///   1. Environment variable `PKM_PYTHON`
///   2. `<engine>/.venv/Scripts/python.exe` (Windows) atau `.venv/bin/python`
///   3. `python` (Windows) / `python3` (lainnya) dari PATH
class ValidatorService {
  /// Batas waktu satu pemeriksaan. Setelah lewat, proses Python dimatikan.
  static const Duration timeout = Duration(minutes: 3);

  static const String _engineDirName = 'python_engine';

  // ==========================================================
  // PATH HELPER
  // ==========================================================

  static String _join(List<String> parts) =>
      parts.join(Platform.pathSeparator);

  static bool _isEngineDir(String dir) =>
      File(_join([dir, 'src', 'validator.py'])).existsSync();

  static String get _bundledExeName =>
      Platform.isWindows ? 'pkm_engine.exe' : 'pkm_engine';

  /// Engine terbungkus: `<folder .exe aplikasi>/engine/pkm_engine(.exe)`.
  static String? _findBundledEngine() {
    final exeDir = File(Platform.resolvedExecutable).parent.path;
    final candidate = _join([exeDir, 'engine', _bundledExeName]);

    return File(candidate).existsSync() ? candidate : null;
  }

  static String? _findEngineDir() {
    final fromEnv = Platform.environment['PKM_ENGINE_DIR'];

    if (fromEnv != null && fromEnv.isNotEmpty && _isEngineDir(fromEnv)) {
      return fromEnv;
    }

    final starts = <Directory>[
      Directory.current,
      File(Platform.resolvedExecutable).parent,
    ];

    for (final start in starts) {
      var dir = start.absolute;

      for (var i = 0; i < 12; i++) {
        final candidates = <String>[dir.path, _join([dir.path, _engineDirName])];

        for (final candidate in candidates) {
          if (_isEngineDir(candidate)) {
            return candidate;
          }
        }

        final parent = dir.parent;

        if (parent.path == dir.path) {
          break;
        }

        dir = parent;
      }
    }

    return null;
  }

  static String _findPython(String engineDir) {
    final fromEnv = Platform.environment['PKM_PYTHON'];

    if (fromEnv != null && fromEnv.isNotEmpty) {
      return fromEnv;
    }

    final venvPython = Platform.isWindows
        ? _join([engineDir, '.venv', 'Scripts', 'python.exe'])
        : _join([engineDir, '.venv', 'bin', 'python']);

    if (File(venvPython).existsSync()) {
      return venvPython;
    }

    return Platform.isWindows ? 'python' : 'python3';
  }

  // ==========================================================
  // VALIDASI
  // ==========================================================

  static Future<Map<String, dynamic>> validate({
    required String pdfPath,
    required String scheme,
  }) async {
    final String executable;
    final List<String> arguments;
    final String workingDirectory;
    final String hint;

    final bundled = _findBundledEngine();

    if (bundled != null) {
      // MODE RILIS: engine Python yang sudah dibungkus.
      executable = bundled;
      arguments = [pdfPath, '--scheme', scheme, '--json'];
      workingDirectory = File(bundled).parent.path;
      hint = 'Folder "engine" di samping aplikasi mungkin rusak atau terblokir '
          'antivirus. Pasang ulang paket aplikasi.';
    } else {
      // MODE PENGEMBANGAN: validator.py lewat Python.
      final engineDir = _findEngineDir();

      if (engineDir == null) {
        throw Exception(
          'Engine pemeriksa tidak ditemukan.\n'
          'Pada mode rilis, folder "engine" harus ada di samping aplikasi. '
          'Pada mode pengembangan, folder "$_engineDirName" (berisi '
          'src/validator.py) harus ada di samping/di atas folder aplikasi, '
          'atau set environment variable PKM_ENGINE_DIR ke lokasinya.',
        );
      }

      executable = _findPython(engineDir);
      arguments = [
        _join([engineDir, 'src', 'validator.py']),
        pdfPath,
        '--scheme',
        scheme,
        '--json',
      ];
      workingDirectory = _join([engineDir, 'src']);
      hint = 'Pastikan virtual environment ada di "$engineDir\\.venv", atau '
          'set environment variable PKM_PYTHON.';
    }

    final Process process;

    try {
      process = await Process.start(
        executable,
        arguments,
        runInShell: false,
        workingDirectory: workingDirectory,
        environment: {'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'},
      );
    } on ProcessException catch (e) {
      throw Exception(
        'Engine tidak bisa dijalankan ("$executable").\n$hint\n${e.message}',
      );
    }

    // Baca stdout/stderr sambil menunggu proses selesai.
    final stdoutFuture = process.stdout.transform(utf8.decoder).join();
    final stderrFuture = process.stderr.transform(utf8.decoder).join();

    final int exitCode;

    try {
      exitCode = await process.exitCode.timeout(timeout);
    } on TimeoutException {
      process.kill();

      throw Exception(
        'Pemeriksaan melebihi batas waktu ${timeout.inMinutes} menit dan '
        'dihentikan. Coba PDF yang lebih kecil atau jalankan ulang.',
      );
    }

    final output = (await stdoutFuture).trim();
    final err = (await stderrFuture).trim();

    // Mode --json selalu mencetak JSON di stdout, termasuk saat error
    // ({"status": "ERROR", "error": "..."}), jadi baca stdout lebih dulu.
    Map<String, dynamic>? parsed;

    try {
      parsed = jsonDecode(output) as Map<String, dynamic>;
    } catch (_) {
      parsed = null;
    }

    if (parsed != null && parsed['status'] == 'ERROR') {
      return parsed;
    }

    if (exitCode != 0) {
      throw Exception('Validator gagal:\n${err.isNotEmpty ? err : output}');
    }

    if (parsed == null) {
      throw Exception('Output Python bukan JSON valid.\n$output');
    }

    return parsed;
  }
}
