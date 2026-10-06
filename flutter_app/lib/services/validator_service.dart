import 'dart:convert';
import 'dart:io';

class ValidatorService {
  static const String pythonPath =
      r'D:\Kuliah\Semester 7\PKM_Checker\python_engine\.venv\Scripts\python.exe';

  static const String validatorPath =
      r'D:\Kuliah\Semester 7\PKM_Checker\python_engine\src\validator.py';

  static Future<Map<String, dynamic>> validate({
    required String pdfPath,
    required String scheme,
  }) async {
    final result = await Process.run(
      pythonPath,
      [
        validatorPath,
        pdfPath,
        '--scheme',
        scheme,
        '--json',
      ],
      runInShell: false,
    );

    if (result.exitCode != 0) {
      throw Exception(
        'Validator gagal:\n${result.stderr}',
      );
    }

    final output = result.stdout.toString();

    try {
      return jsonDecode(output) as Map<String, dynamic>;
    } catch (e) {
      throw Exception(
        'Output Python bukan JSON valid.\n$output',
      );
    }
  }
}
