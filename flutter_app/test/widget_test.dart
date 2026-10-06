import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_app/main.dart';

void main() {
  testWidgets('PKM Checker membuka halaman utama', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const PKMCheckerApp());

    expect(find.text('PKM 2026 Checker'), findsWidgets);
    expect(find.text('Pilih PDF'), findsOneWidget);
    expect(find.text('Periksa Dokumen'), findsOneWidget);
    expect(find.text('Skema PKM'), findsOneWidget);
  });
}