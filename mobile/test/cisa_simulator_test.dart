import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:grc_ustasi/main.dart';
import 'package:grc_ustasi/theme.dart';
import 'package:grc_ustasi/interactive_questions.dart';
import 'package:grc_ustasi/workshop_questions.dart';
void main() {
  final pack=jsonDecode(File('../content/learning-paths/cisa-auditor-simulator/package.json').readAsStringSync()) as Map;
  final records=pack['questions'] as List;
  for(final index in [0,1,2,3,4,5,10,31]) {
    testWidgets('CISA task ${index+1}: direct start and supported renderer', (tester) async {
      tester.view.devicePixelRatio=1;tester.view.physicalSize=const Size(430,932);
      addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
      SharedPreferences.setMockInitialValues({});
      final q=Map<String,dynamic>.from(records[index] as Map);
      q['id']=index+1;q['audio']=<String>[];q['image']=null;
      final api=WorkshopQuestionApi(q);
      const path = {'id':99,'title':'CISA: Gerçek Bir IT Denetçisi Olabilir misin? 🎯','direct_start':true,'question_count':100};
      await tester.pumpWidget(MaterialApp(
        theme:AppTheme.create(Brightness.light),
        home:Builder(builder:(context) => Scaffold(
          body:PathCard(path:path,onTap:() {
            Navigator.of(context).push(MaterialPageRoute(
              builder: (_) => Session(path:path,sessionApi:api,workshop:true),
            ));
          }),
        )),
      ));
      await tester.pumpAndSettle();await tester.tap(find.byType(PathCard));await tester.pumpAndSettle();expect(find.text('Başla'),findsNothing);
      await tester.scrollUntilVisible(find.text(q['prompt'] as String),200,scrollable:find.byType(Scrollable).first);
      expect(find.text(q['prompt'] as String),findsOneWidget);expect(find.text('Senaryoyu dinle'),findsNothing);
      if(q['kind']=='sentence_order' || q['kind']=='drag_select') {
        final renderer=q['kind']=='sentence_order'?find.byType(SentenceBuilder):find.byType(DragRiskQuestion);
        await tester.scrollUntilVisible(renderer,200,scrollable:find.byType(Scrollable).first);expect(renderer,findsOneWidget);
      } else if(q['kind']=='fill_blank') {
        final field=find.widgetWithText(TextField,'Yanıtın');await tester.scrollUntilVisible(field,200,scrollable:find.byType(Scrollable).first);await tester.enterText(field,'kontrol');
      } else {
        final text=(q['options'] as List).first['text'] as String;
        await tester.scrollUntilVisible(find.text(text),200,scrollable:find.byType(Scrollable).first);await tester.tap(find.text(text));await tester.pump();
        expect(tester.widget<AnswerOption>(find.ancestor(of:find.text(text),matching:find.byType(AnswerOption))).selected,true);
      }
      expect(tester.takeException(),isNull);await tester.pumpWidget(const SizedBox.shrink());await tester.pumpAndSettle();api.client.close();
    });
  }
}
