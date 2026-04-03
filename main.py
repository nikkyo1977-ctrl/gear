import argparse
import sys
from gears import create_spur_gear, create_helical_gear, create_rack_gear, create_worm_zi

def export_part(part, filename):
    print(f"Esportazione del modello in {filename}...")
    try:
        from build123d import export_step
        part.export_step(filename)
    except AttributeError:
        # Fallback if export_step is a module-level function depending on build123d version
        try:
            import cadquery as cq
            # build123d parts under the hood are TopoDS_Shape wrappers, but part.export_step usually works
            part.export_step(filename)
        except Exception as e:
            print(f"Errore: esportazione STEP fallita - {e}")
            from build123d import export_step
            export_step(part, filename)
    print("Esportazione completata con successo.")

def main():
    parser = argparse.ArgumentParser(description="Python Gear Generator (Simil-KISSsoft)")
    subparsers = parser.add_subparsers(dest="type", help="Tipo di ingranaggio", required=True)

    # Spur gear parser
    parser_spur = subparsers.add_parser('spur', help="Ingranaggio a denti dritti")
    parser_spur.add_argument('-m', '--module', type=float, required=True, help="Modulo (mm)")
    parser_spur.add_argument('-z', '--teeth', type=int, required=True, help="Numero di denti")
    parser_spur.add_argument('-w', '--width', type=float, required=True, help="Fascia / Larghezza (mm)")
    parser_spur.add_argument('-a', '--alpha', type=float, default=20.0, help="Angolo di pressione (deg)")
    parser_spur.add_argument('-x', '--shift', type=float, default=0.0, help="Coefficiente spostamento profilo")
    parser_spur.add_argument('-o', '--output', type=str, default="spur_gear.stp", help="Nome file di output")

    # Helical gear parser
    parser_helical = subparsers.add_parser('helical', help="Ingranaggio elicoidale")
    parser_helical.add_argument('-m', '--module', type=float, required=True, help="Modulo normale (mm)")
    parser_helical.add_argument('-z', '--teeth', type=int, required=True, help="Numero di denti")
    parser_helical.add_argument('-w', '--width', type=float, required=True, help="Fascia / Larghezza (mm)")
    parser_helical.add_argument('-b', '--beta', type=float, required=True, help="Angolo d'elica (deg)")
    parser_helical.add_argument('-a', '--alpha', type=float, default=20.0, help="Angolo di pressione normale (deg)")
    parser_helical.add_argument('-o', '--output', type=str, default="helical_gear.stp", help="Nome file di output")

    # Rack gear parser
    parser_rack = subparsers.add_parser('rack', help="Cremagliera")
    parser_rack.add_argument('-m', '--module', type=float, required=True, help="Modulo (mm)")
    parser_rack.add_argument('-z', '--teeth', type=int, required=True, help="Numero di denti in lunghezza")
    parser_rack.add_argument('-w', '--width', type=float, required=True, help="Fascia / Larghezza (mm)")
    parser_rack.add_argument('-o', '--output', type=str, default="rack_gear.stp", help="Nome file di output")

    # Worm gear parser
    parser_worm = subparsers.add_parser('worm', help="Vite senza fine ZI")
    parser_worm.add_argument('-m', '--module', type=float, required=True, help="Modulo assiale (mm)")
    parser_worm.add_argument('-z', '--starts', type=int, required=True, help="Numero di princìpi (denti)")
    parser_worm.add_argument('-q', '--quotient', type=float, required=True, help="Quoziente diametrale d1/m")
    parser_worm.add_argument('-l', '--length', type=float, required=True, help="Lunghezza della vite (mm)")
    parser_worm.add_argument('-o', '--output', type=str, default="worm_zi.stp", help="Nome file di output")

    args = parser.parse_args()

    print(f"Avvio generazione {args.type}...")
    try:
        if args.type == 'spur':
            part = create_spur_gear(args.module, args.teeth, args.width, args.alpha, args.shift)
            export_part(part, args.output)
        elif args.type == 'helical':
            part = create_helical_gear(args.module, args.teeth, args.width, args.beta, args.alpha)
            export_part(part, args.output)
        elif args.type == 'rack':
            part = create_rack_gear(args.module, args.teeth, args.width)
            export_part(part, args.output)
        elif args.type == 'worm':
            part = create_worm_zi(args.module, args.starts, args.quotient, args.length)
            export_part(part, args.output)
    except Exception as e:
        print(f"Errore durante la generazione: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
