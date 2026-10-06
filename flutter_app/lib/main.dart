import 'package:flutter/material.dart';

import 'screens/home_screen.dart';

void main() {
  runApp(const PKMCheckerApp());
}

class PKMCheckerApp extends StatelessWidget {
  const PKMCheckerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PKM Checker',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}
