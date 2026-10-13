import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:grc_ustasi/fullscreen_image_viewer.dart';
void main(){
 final provider=MemoryImage(base64Decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1sAAAAASUVORK5CYII='));
 testWidgets('preview opens viewer, zoom resets, ESC returns selected answer', (tester)async{
  await tester.pumpWidget(MaterialApp(home:Scaffold(body:Column(children:[QuestionImagePreview(imageProvider:provider),Checkbox(value:true,onChanged:(_) {})]))));await tester.pumpAndSettle();
  expect(tester.getSize(find.byType(Image)).height,220);await tester.tap(find.byType(InkWell).first);await tester.pumpAndSettle();expect(find.byType(FullscreenImageViewer),findsOneWidget);
  final viewer=tester.widget<InteractiveViewer>(find.byType(InteractiveViewer));await tester.tap(find.byTooltip('Yakınlaştır'));await tester.pump();expect(viewer.transformationController!.value.getMaxScaleOnAxis(),2);
  await tester.tap(find.byTooltip('Zoom sıfırla'));await tester.pump();expect(viewer.transformationController!.value.getMaxScaleOnAxis(),1);
  await tester.sendKeyEvent(LogicalKeyboardKey.escape);await tester.pumpAndSettle();expect(find.byType(FullscreenImageViewer),findsNothing);expect(tester.widget<Checkbox>(find.byType(Checkbox)).value,true);
 });
 testWidgets('pinch, pan and close work in the viewer', (tester)async{
  await tester.pumpWidget(MaterialApp(home:FullscreenImageViewer(imageProvider:provider)));await tester.pumpAndSettle();final iv=tester.widget<InteractiveViewer>(find.byType(InteractiveViewer));
  final a=await tester.startGesture(const Offset(300,250),pointer:1);final b=await tester.startGesture(const Offset(400,250),pointer:2);await tester.pump();await a.moveTo(const Offset(250,250));await b.moveTo(const Offset(450,250));await tester.pump();expect(iv.transformationController!.value.getMaxScaleOnAxis(),greaterThan(1));await a.up();await b.up();await tester.pump(const Duration(milliseconds:400));final before=iv.transformationController!.value.getTranslation().x;await tester.drag(find.byType(InteractiveViewer),const Offset(50,0));await tester.pumpAndSettle();expect(iv.transformationController!.value.getTranslation().x,isNot(before));
  await tester.tap(find.byTooltip('Ekrana sığdır'));await tester.pump();expect(iv.transformationController!.value.getMaxScaleOnAxis(),1);await tester.pump(const Duration(seconds:1));expect(tester.takeException(),isNull);
 });
}
