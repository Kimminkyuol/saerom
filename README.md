# 새롬

한국어 문법을 따르는 프로그래밍 언어.

```
통계에서 평균을 가져온다.

학생은 이런 것이다:
    이름은 문자열이다.
    점수들은 정수들이다.

학생의 평균점수라는 것은:
    학생의 점수들의 평균을 돌려준다.

철수는 이름이 "김철수"이고 점수들이 [88, 92, 79]인 학생이다.

"{철수의 이름}: {철수의 평균점수}점\n"을 출력한다.
```

## 설치

```
pip install -e .
```

## 사용

```
saerom <파일.sr>              프로그램 실행
saerom --format <파일.sr>...  형식 교정
saerom --check  <파일.sr>...  형식 검사
saerom --lsp                 언어 서버 (편집기용)
```

## VS Code 확장

```
make install-extension
```

## 문서

- [예시](examples/)
- [새롬 문법](docs/rules.md)
- [새롬 도구](docs/tools.md)

## 개발

```
make test      단위 검사
make examples  예시 전부 실행
make check     표준 라이브러리 형식 검사
make format    표준 라이브러리 형식 교정
make vsix      VS Code 확장 패키징 (vsce 필요)
```

## 라이선스

MIT
