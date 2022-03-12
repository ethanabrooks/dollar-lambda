{
  description = "TODO";
  inputs = {
    nixpkgs.url = "nixpkgs/nixos-21.11";
    # nixpkgs.url = "nixpkgs/nixos-unstable";
    pytypeclass.url = "path:/Users/alec/pytypeclass";
  };
  outputs = { self, nixpkgs, pytypeclass }:
    (let systems = [ "x86_64-darwin" ];
    in {
      packages = nixpkgs.lib.genAttrs systems (system:
        let
          pkgs = (nixpkgs.lib.genAttrs systems
            (system: import nixpkgs { inherit system; })).${system};
        in {
          devShell = pkgs.mkShell {
            buildInputs = [ pkgs.gnumake pkgs.python310 ];
            shellHook = ''
              [ -d .venv ] || python -m venv .venv
              .venv/bin/pip install --upgrade pip
              .venv/bin/pip install poetry
              .venv/bin/poetry install
            '';
          };
          dollar-lambda = (pkgs.python310Packages.buildPythonPackage {
            name = "dollar-lambda";
            src = ./.;
            propagatedBuildInputs = [ pytypeclass.defaultPackage.${system} ];
          });
        });
      defaultPackage = nixpkgs.lib.genAttrs systems
        (system: self.packages.${system}.dollar-lambda);
    });
}
