import battle_model

walka = battle_model.BattleModel(3,5,5,3,5,5,70,70)
a = True
while a:
    a = walka.step()

print("Bitwa została zakończona.")