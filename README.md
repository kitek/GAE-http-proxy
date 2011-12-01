## GAE-http-proxy


GAE-http-proxy jest prostym HTTP proxy opartym o [Google App Engine](http://code.google.com/appengine).

---

### Konfiguracja
Do poprawnego działania proxy wymagane jest ustawienie następujących ustawień.

Plik *app.yaml*:

* application: APP_ID # Nasz identyfikator z GAE

Plik: *main.py*:

* HTTP_PREFIX = "http://SOURCE/" # URL do zasobu, który chcemy keszować

### Uruchomienie

Po wykonaniu deploy'a do GAE możemy zacząć korzystać z naszego proxy wykorzystując adres: http://app_id.appspot.com/sciezka/plik

### Limity

Aplikacje oparte o GAE posiadają liczne [limity](http://code.google.com/appengine/docs/quotas.html).
