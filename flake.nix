{
  description = "";
  inputs = { nixpkgs.url = "nixpkgs/nixos-21.11"; };
  outputs = { self, nixpkgs }:
    (let systems = [ "x86_64-darwin" ];
    in {
      packages = nixpkgs.lib.genAttrs systems (system:
        let pkgs = import nixpkgs { inherit system; };
        in {
          devShell = pkgs.mkShell {
            buildInputs = [ pkgs.gnumake pkgs.just pkgs.nixfmt pkgs.python310 ];
            shellHook = ''
              [ -d .venv ] || python -m venv .venv
              .venv/bin/pip install --upgrade pip
              .venv/bin/pip install poetry
              .venv/bin/poetry install
            '';
          };
        });
    });
}
