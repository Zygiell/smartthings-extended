# Pierwsza publikacja na GitHub

Repo jest gotowe do publikacji, ale przed pierwszym pushem trzeba wstawić
Twój GitHub username do `manifest.json`.

## 1. Uzupełnij ownera

```bash
python3 scripts/configure_repo.py TWOJ_GITHUB_USERNAME
```

## 2. Utwórz publiczne repo `smartthings-extended`

Najwygodniej przez GitHub UI: nowe **publiczne** repo o nazwie:

```text
smartthings-extended
```

Nie dodawaj README/licencji/.gitignore z GitHuba — te pliki już są tutaj.

Ustaw krótki opis repo, np.:

```text
Home Assistant custom integration extending Samsung SmartThings appliance controls.
```

Dobrze dodać topics:

```text
home-assistant
hacs
smartthings
samsung
custom-component
```

## 3. Pierwszy push

W katalogu repo:

```bash
git init
git add .
git commit -m "Initial HACS release v0.2.1"
git branch -M main
git remote add origin https://github.com/TWOJ_GITHUB_USERNAME/smartthings-extended.git
git push -u origin main
```

Jeżeli używasz SSH:

```bash
git remote add origin git@github.com:TWOJ_GITHUB_USERNAME/smartthings-extended.git
```

## 4. Sprawdź Actions

Na GitHubie otwórz **Actions**. Powinny uruchomić się:

- Validate HACS
- Validate with hassfest

## 5. Release

Po zielonych Actions utwórz pełny GitHub Release (nie tylko tag):

```text
v0.2.1
```

Jeśli masz GitHub CLI:

```bash
gh release create v0.2.1 \
  --title "SmartThings Extended v0.2.1" \
  --notes-file CHANGELOG.md
```

Możesz też zrobić release normalnie w GitHub UI.

## 6. HACS

W Home Assistant:

HACS -> menu `...` -> Custom repositories

Dodaj:

```text
https://github.com/TWOJ_GITHUB_USERNAME/smartthings-extended
```

Typ:

```text
Integration
```

Potem Download/Redownload i restart Home Assistant.

## Aktualizacje później

Przy kolejnych wersjach:

1. zmieniamy `version` w `manifest.json`
2. commit + push
3. czekamy na zielone Actions
4. tworzymy GitHub Release, np. `v0.3.0`
5. HACS pokaże aktualizację
