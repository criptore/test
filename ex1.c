#include <allegro.h>
#include <iostream>
#include <vector>

// Structures de données simplifiées pour l'exemple
struct Entite {
    int x, y;
    int pv;
    int pa; // Points d'action
    int pm; // Points de mouvement

    void deplacer(int dx, int dy) {
        x += dx;
        y += dy;
        pm -= abs(dx) + abs(dy);
    }

    void attaquer(Entite& cible) {
        cible.pv -= 5; // Attaque basique
        pa -= 2; // Coût en PA
    }
};

int main() {
    allegro_init();
    install_keyboard();
    set_color_depth(32);
    set_gfx_mode(GFX_AUTODETECT_WINDOWED, 800, 600, 0, 0);

    BITMAP* buffer = create_bitmap(SCREEN_W, SCREEN_H);

    // Création des entités (joueur et ennemi)
    Entite joueur = {100, 100, 100, 6, 3};
    Entite ennemi = {500, 300, 50, 4, 2};

    bool tourJoueur = true;

    while (!key[KEY_ESC]) {
        clear_to_color(buffer, makecol(255, 255, 255));

        // Affichage des entités (simplifié)
        circlefill(buffer, joueur.x, joueur.y, 10, makecol(0, 0, 255)); // Joueur en bleu
        circlefill(buffer, ennemi.x, ennemi.y, 10, makecol(255, 0, 0)); // Ennemi en rouge


        if (tourJoueur) {
            if (key[KEY_LEFT] && joueur.pm > 0)  joueur.deplacer(-10, 0);
            if (key[KEY_RIGHT]&& joueur.pm > 0) joueur.deplacer(10, 0);
            if (key[KEY_UP]   && joueur.pm > 0) joueur.deplacer(0, -10);
            if (key[KEY_DOWN] && joueur.pm > 0) joueur.deplacer(0, 10);

            if (key[KEY_SPACE] && joueur.pa >= 2) { // Attaque
                joueur.attaquer(ennemi);
                tourJoueur = false; // Fin du tour du joueur
                joueur.pa = 6; // Reset PA
                joueur.pm = 3; // Reset PM
            }
        } else { // Tour de l'ennemi (IA basique)
            if (ennemi.pa >= 2) {
                ennemi.attaquer(joueur);
                tourJoueur = true; // Fin du tour de l'ennemi
                ennemi.pa = 4; // Reset PA
                ennemi.pm = 2; // Reset PM
            } else {
                tourJoueur = true;
                ennemi.pa = 4; // Reset PA
                ennemi.pm = 2; // Reset PM
            }
        }

        textprintf_ex(buffer, font, 10, 10, makecol(0,0,0), -1, "Joueur PV: %d PA: %d PM: %d", joueur.pv, joueur.pa, joueur.pm);
        textprintf_ex(buffer, font, 10, 30, makecol(0,0,0), -1, "Ennemi PV: %d PA: %d PM: %d", ennemi.pv, ennemi.pa, ennemi.pm);

        blit(buffer, screen, 0, 0, 0, 0, SCREEN_W, SCREEN_H);

        rest(10); // Petite pause pour éviter une boucle trop rapide
    }

    destroy_bitmap(buffer);
    return 0;
}
END_OF_MAIN()