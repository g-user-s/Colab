#!/usr/bin/env python3
"""google-colab-cli 0.8.0 için 411 Length Required yaması.

Sorun: CLI runtime açma/kapatma isteklerini gövdesiz POST ile gönderiyor; Colab ön yüzü 411 ile reddediyor.
Çözüm: gövdesiz POST'lara boş JSON gövde ({}) eklenir.

Kullanım (CLI'nın venv'indeki python ile):
  ~/workspace/tools/colab-cli-venv/bin/python muse/yama_411.py           # uygula (zaten uygulandıysa dokunmaz)
  ~/workspace/tools/colab-cli-venv/bin/python muse/yama_411.py --kontrol # yalnızca kontrol et
  python muse/yama_411.py --dosya /yol/colab_cli/client.py                # belirli bir dosyaya uygula

Paket güncellenir ya da yeniden kurulursa yama silinir: bu betiği yeniden çalıştır.
Çıkış kodları: 0 = yama yerinde, 1 = yama yok (--kontrol) ya da uygulanamadı.
"""

import argparse
import importlib.util
import os
import re
import sys

ISARET = "# h3muse-411-yamasi"
HEDEF = """        response = self.session.request(
            method, endpoint, headers=request_headers, params=params, **kwargs
        )"""
YAMA = f"""        if method.upper() == "POST" and "json" not in kwargs and "data" not in kwargs:  {ISARET}
            kwargs["json"] = {{}}  {ISARET}
""" + HEDEF


def islevsel_yama_var(metin):
    """Elle yapılmış eşdeğer yamayı tanır: _issue_request içinde, istekten önce kwargs["json"] = {} ataması."""
    bas = metin.find("def _issue_request(")
    if bas < 0:
        return False
    govde = metin[bas:metin.find("self.session.request(", bas)]
    return bool(re.search(r"""kwargs\[\s*["']json["']\s*\]\s*=\s*\{\s*\}""", govde)) and "POST" in govde


def client_yolu():
    spec = importlib.util.find_spec("colab_cli")
    if not spec or not spec.submodule_search_locations:
        raise SystemExit("colab_cli bu python'da kurulu değil. CLI'nın venv'indeki python ile çalıştır.")
    return os.path.join(list(spec.submodule_search_locations)[0], "client.py")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--dosya", help="client.py yolu (varsayılan: kurulu colab_cli)")
    p.add_argument("--kontrol", action="store_true", help="Değiştirme, yalnızca durumu söyle")
    a = p.parse_args(argv)
    yol = a.dosya or client_yolu()
    metin = open(yol, encoding="utf-8").read()
    if ISARET in metin:
        print(f"✅ Yama zaten uygulanmış: {yol}")
        return 0
    if islevsel_yama_var(metin):
        print(f"✅ Yama işlevsel olarak var (elle uygulanmış, işaretsiz): {yol}\n"
              "   _issue_request gövdesiz POST'lara json={} ekliyor; yeniden uygulamaya gerek yok.")
        return 0
    if a.kontrol:
        print(f"❌ Yama yok: {yol}")
        return 1
    if metin.count(HEDEF) != 1:
        print(f"❌ Beklenen kod bulunamadı (CLI sürümü değişmiş olabilir): {yol}\n"
              "Yamayı elle uygulama; durumu orhan'a bildir.")
        return 1
    with open(yol + ".yamasiz", "w", encoding="utf-8") as f:
        f.write(metin)
    yeni = metin.replace(HEDEF, YAMA)
    compile(yeni, yol, "exec")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(yeni)
    print(f"✅ Yama uygulandı: {yol} (yedek: {yol}.yamasiz)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
