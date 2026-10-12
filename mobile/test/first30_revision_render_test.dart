import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:grc_ustasi/main.dart';
import 'package:grc_ustasi/theme.dart';
import 'package:grc_ustasi/interactive_questions.dart';
import 'package:grc_ustasi/information_card.dart';
import 'package:grc_ustasi/workshop_questions.dart';
void main() {
  final pack=jsonDecode(File('../content/learning-paths/first-30-days/v2/package.json').readAsStringSync()) as Map;
  final records=pack['questions'] as List;
  for(final number in [1,2,3,4,5,6,7,8,9,10]) {
    testWidgets('First30 revised slot $number renders at phone width', (tester) async {
      tester.view.devicePixelRatio=1;tester.view.physicalSize=const Size(430,932);
      addTearDown(tester.view.resetPhysicalSize);addTearDown(tester.view.resetDevicePixelRatio);
      SharedPreferences.setMockInitialValues({});
      final q=Map<String,dynamic>.from(records[number-1] as Map);
      q['id']=number;q['audio']=q['kind']=='audio'?<String>['https://example.invalid/audio.mp3']:<String>[];q['image']=null;
      final api=WorkshopQuestionApi(q);
      await tester.pumpWidget(MaterialApp(theme:AppTheme.create(Brightness.light),home:Session(path:const {'id':26,'title':'İşe Alındın! İlk 30 Günün'},sessionApi:api,workshop:true)));
      await tester.tap(find.text('Başla'));await tester.pumpAndSettle();
      if(q['kind']=='info') {expect(find.byType(InformationCard),findsOneWidget);}
      else {
        await tester.scrollUntilVisible(find.text(q['prompt'] as String),200,scrollable:find.byType(Scrollable).first);
        expect(find.text(q['prompt'] as String),findsOneWidget);
        if(q['kind']=='audio') {
          await tester.scrollUntilVisible(find.text('Senaryoyu dinle'),200,scrollable:find.byType(Scrollable).first);
          expect(find.text('Senaryoyu dinle'),findsOneWidget);
        } else {expect(find.text('Senaryoyu dinle'),findsNothing);}
        if(q['kind']=='sentence_order' || q['kind']=='drag_select') {
          final widget=q['kind']=='sentence_order'?find.byType(SentenceBuilder):find.byType(DragRiskQuestion);
          await tester.scrollUntilVisible(widget,200,scrollable:find.byType(Scrollable).first);expect(widget,findsOneWidget);
        } else if(q['kind']=='fill_blank') {
          final field=find.widgetWithText(TextField,'Yanıtın');
          await tester.scrollUntilVisible(field,200,scrollable:find.byType(Scrollable).first);await tester.enterText(field,'gizlilik');
        } else {
          final first=(q['options'] as List).first['text'] as String;
          await tester.scrollUntilVisible(find.text(first),200,scrollable:find.byType(Scrollable).first);
          await tester.tap(find.text(first));await tester.pump();
          final option=find.ancestor(of:find.text(first),matching:find.byType(AnswerOption));
          expect(tester.widget<AnswerOption>(option).selected,true);
        }
      }
      expect(tester.takeException(),isNull);
      await tester.pumpWidget(const SizedBox.shrink());await tester.pumpAndSettle();api.client.close();
    });
  }
}
