{
  description = "";
  inputs = { nixpkgs.url = "nixpkgs/nixos-21.11"; };
  outputs = { self, nixpkgs }: {
    packages = nixpkgs.lib.genAttrs [ "x86_64-darwin" ] (system:
      let pkgs = import nixpkgs { inherit system; };
      in {
        devShell = pkgs.mkShell {
          buildInputs = [
            pkgs.ninja
            pkgs.git
            pkgs.nixfmt
            pkgs.shellcheck
            pkgs.shfmt
            pkgs.fd
            pkgs.rsync
            pkgs.nodePackages.prettier
            pkgs.python310
          ];
          # There were some issues with automatically installing Poetry and
          # mypy on macOS with Python 3.10 using pkgs.python310Packages, so in
          # the shell hook we manually create a virtualenv, upgrade Pip,
          # install Poetry, then use Poetry to install dependencies. This also
          # allows someone to use Poetry to install this Python environment
          # without using Nix.
          shellHook = ''
            [ -d .venv ] || python -m venv .venv
            .venv/bin/pip install --upgrade pip
            .venv/bin/pip install poetry
            .venv/bin/poetry install
          '';
        };
      });
  };
}
