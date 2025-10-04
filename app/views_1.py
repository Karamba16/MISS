from deeppavlov import build_model, configs

ner_model = build_model(configs.ner.ner_bert_mult, download=True)
text = ["Владимир Путин встретился с президентом Казахстана Касым-Жомартом Токаевым в Москве."]
print(ner_model(text))