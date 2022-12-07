Monitor stworzony wykorzystując algorytm Suzuki-Kasami w którym krąży token zezwalający na wejście do sekcji krytycznej.
Przedawnione żądania są pilnowane przez tablice rn pilnująca liczbe porządkową żądań każdego z procesów, tablicy żetonu ln
oraz kolejki żetonu token_queue.

Użytkownik korzystając z monitora musi w każdym procesie stworzyć obiekt monitora podając jako argumenty:
	- tablice portów wszystkich procesów systemu (tutaj w ports_file.py znajduje sie ta tablica)
	- port tego konkretnego procesu
	- 0 albo 1 określający który proces zacznie z tokenem (tylko jeden proces może mieć token)

W ramach testu przygotowałem problem producent-konsument w którym określiem wielkośc buffora oraz maksymalna wartość.
Udostepniam użytkownikowi 5 funkcji oraz dostęp do danych.
	- enter_cs() funkcją próbujemy dostać sie do sekcji krytycznej
	- leave_cs() odpowiednik funkcji wyżej, opuszczamy sekcje krytyczną
	- read_data() wyciągamy dane z monitora
	- add_data() wkładamy dane do monitora
	- stop_all() ma za zadanie zakonczyc wszystkie procesy w systemie
	- data to w zasadzie tablica danych dostepna do uzytkownika caly czas
	- last_value to ostatnia liczba dodana do tablicy data
	
Uzytkownik musi pilnowac wielkosc tablicy data aby odpowiednio inkrementowac te dane.
Wszystko możemy uruchomic z pliku main w który zesynchronizuje nam włączenie procesów. 


buffor operacji
monitor typu buffo put,get