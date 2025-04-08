/*******************************************************************
BITMAP : Charger une image depuis un fichier .bmp vers une BITMAP
         et afficher cette BITMAP au milieu de l'écran

         L'image s'apppelle "bonhomme" et doit être mise
         au niveau du répertoire de projet (avec le main.c)
         à moins de modifier le chemin d'accès ci dessous...

         Appuyer sur espace pour afficher l'image à une position aléatoire
         Appuyer sur la flèche du haut pour faire monter l'image
         Appuyer sur la flèche du bas pour faire descendre l'image
         Appuyer sur la touche Entrée pour recentrer l'image
*******************************************************************/

#include <allegro.h>
#include <time.h>

void initialisation_allegro();

int main()
{
    // Déclaration du pointeur sur BITMAP devant recevoir l'image
    BITMAP *image;
    int touche;
    int x, y;
    // Il y aura un peu de hasard...
    srand(time(NULL));

    // Lancer allegro et le mode graphique
    allegro_init();
    install_keyboard();

    set_color_depth(desktop_color_depth());
    if (set_gfx_mode(GFX_AUTODETECT_WINDOWED, 800, 600, 0, 0) != 0)
    {
        allegro_message("prb gfx mode");
        allegro_exit();
        exit(EXIT_FAILURE);
    }

    // Chargement de l'image (l'allocation a lieu en même temps)
    image = load_bitmap("bonhomme.bmp", NULL);

    // Vérification que l'image est bien chargée (dans le cas contraire image vaut NULL)
    // TOUJOURS LE FAIRE CAR ON N'EST JAMAIS CERTAIN DE BIEN TROUVER L'IMAGE
    if (!image)
    {
        allegro_message("pas pu trouver/charger mon_image.bmp");
        allegro_exit();
        exit(EXIT_FAILURE);
    }

    // Affichage de l'image sur l'écran au milieu
    blit(image, screen, 0, 0, (SCREEN_W - image->w) / 2, (SCREEN_H - image->h) / 2, image->w, image->h);
    x = (SCREEN_W - image->w) / 2;
    y = (SCREEN_H - image->h) / 2;
    int depx = 5;
    int depy = 5;

    // Boucle interactive
    while (!key[KEY_ESC]) {
        if (keypressed()) {
            touche = readkey();
            touche = touche >> 8;
            if (touche == KEY_SPACE) {
                x = rand() % (SCREEN_W - image->w);
                y = rand() % (SCREEN_H - image->h);
            }
            if (touche == KEY_UP) {
                if (y - depy > 0) y -= depy;
            }
            if (touche == KEY_DOWN) {
                if (y + image->h + depy < SCREEN_H) y += depy;
            }
            if (touche == KEY_LEFT) {
                if (x - depx > 0) x -= depx;
            }
            if (touche == KEY_RIGHT) {
                if (x + image->w + depx < SCREEN_W) x += depx;
            }
            if (touche == KEY_ENTER) {
                x = (SCREEN_W - image->w) / 2;
                y = (SCREEN_H - image->h) / 2;
            }
            clear_bitmap(screen);
            blit(image, screen, 0, 0, x, y, image->w, image->h);
        }
    }
    // quand on a plus besoin de la bitmap, on la détruit
    destroy_bitmap(image);
    allegro_exit();
    return 0;
}
END_OF_MAIN();

void initialisation_allegro() {
    allegro_init(); // appel obligatoire (var.globales, recup. infos syst me ...)
    install_keyboard(); // pour utiliser le clavier
    install_mouse(); // pour utiliser la souris
    // pour choisir la profondeur de couleurs (8,16,24 ou 32 bits)
    set_color_depth(desktop_color_depth()); // ici : identique à celle du bureau

    // sélection du mode graphique
    // avec choix d'un driver+mode+résolution de l'écran
    // si échec, le programme s'arrête
    if (set_gfx_mode(GFX_AUTODETECT_WINDOWED, 800, 600, 0, 0) != 0)
    {
        allegro_message("probleme mode graphique");
        allegro_exit();
        exit(EXIT_FAILURE);
    }
}
