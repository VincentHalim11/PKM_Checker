import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../services/validator_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  String? _selectedPdfPath;
  String _selectedScheme = 'K';

  String _status = 'Belum diuji';
  bool _isLoading = false;
  String? _error;

  Future<void> _pickPdf() async {
    final file = await FilePicker.pickFile(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
    );

    if (file != null && file.path != null) {
      setState(() {
        _selectedPdfPath = file.path;
        _status = 'Belum diuji';
        _error = null;
      });
    }
  }

  Future<void> _runValidator() async {
    if (_selectedPdfPath == null) {
      setState(() {
        _error = 'Silakan pilih file PDF terlebih dahulu.';
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _status = 'Sedang memeriksa...';
      _error = null;
    });

    try {
      final result = await ValidatorService.validate(
        pdfPath: _selectedPdfPath!,
        scheme: _selectedScheme,
      );

      setState(() {
        _status = result['status']?.toString() ?? 'UNKNOWN';
      });
    } catch (e) {
      setState(() {
        _status = 'ERROR';
        _error = e.toString();
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('PKM Checker Test'),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text(
                'Flutter → Python → JSON',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),

              const SizedBox(height: 30),

              const Text(
                'File PDF',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),

              const SizedBox(height: 10),

              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 800),
                child: Text(
                  _selectedPdfPath ?? 'Belum ada file dipilih',
                  textAlign: TextAlign.center,
                ),
              ),

              const SizedBox(height: 15),

              ElevatedButton.icon(
                onPressed: _isLoading ? null : _pickPdf,
                icon: const Icon(Icons.folder_open),
                label: const Text('Pilih PDF'),
              ),

              const SizedBox(height: 30),

              const Text(
                'Skema PKM',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),

              const SizedBox(height: 10),

              DropdownButton<String>(
                value: _selectedScheme,
                items: const [
                  DropdownMenuItem(
                    value: 'GFT',
                    child: Text('PKM-GFT'),
                  ),
                  DropdownMenuItem(
                    value: 'AI',
                    child: Text('PKM-AI'),
                  ),
                  DropdownMenuItem(
                    value: 'K',
                    child: Text('PKM-K'),
                  ),
                  DropdownMenuItem(
                    value: 'KC',
                    child: Text('PKM-KC'),
                  ),
                  DropdownMenuItem(
                    value: 'KI',
                    child: Text('PKM-KI'),
                  ),
                  DropdownMenuItem(
                    value: 'PI',
                    child: Text('PKM-PI'),
                  ),
                  DropdownMenuItem(
                    value: 'PM',
                    child: Text('PKM-PM'),
                  ),
                  DropdownMenuItem(
                    value: 'RE',
                    child: Text('PKM-RE'),
                  ),
                  DropdownMenuItem(
                    value: 'RSH',
                    child: Text('PKM-RSH'),
                  ),
                  DropdownMenuItem(
                    value: 'VGK',
                    child: Text('PKM-VGK'),
                  ),
                ],
                onChanged: _isLoading
                    ? null
                    : (value) {
                        if (value != null) {
                          setState(() {
                            _selectedScheme = value;
                            _status = 'Belum diuji';
                            _error = null;
                          });
                        }
                      },
              ),

              const SizedBox(height: 20),

              ElevatedButton(
                onPressed: _isLoading ? null : _runValidator,
                child: Text(
                  _isLoading ? 'Memeriksa...' : 'Jalankan Validator',
                ),
              ),

              const SizedBox(height: 30),

              Text(
                'Status: $_status',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),

              if (_error != null) ...[
                const SizedBox(height: 20),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 800),
                  child: Text(
                    _error!,
                    textAlign: TextAlign.center,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
