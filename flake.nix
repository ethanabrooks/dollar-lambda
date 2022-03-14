{
  description = "";
  inputs = { nixpkgs.url = "nixpkgs/nixos-21.11"; };
  outputs = { self, nixpkgs }: {
    packages = nixpkgs.lib.genAttrs [ "x86_64-darwin" ] (system:
      let pkgs = import nixpkgs { inherit system; };
      in {
        devShell = pkgs.mkShell {
          buildInputs = [
            pkgs.fd
            pkgs.git
            pkgs.ninja
            pkgs.nixfmt
            pkgs.just
            pkgs.nodePackages.prettier
            pkgs.python310
            pkgs.rsync
            pkgs.shellcheck
            pkgs.shfmt
          ];
          # There were some issues with automatically installing Poetry and mypy
          # on macOS with Python 3.10 using pkgs.python310Packages, so in the
          # shell hook we manually create a virtualenv, upgrade Pip, install
          # Poetry, then use Poetry to install dependencies. This also allows
          # someone to use Poetry to install this Python environment without
          # using Nix and simultaneously take advantage of the benefits of both
          # Nix and Poetry.
          shellHook = ''
            just init-poetry
          '';
        };
      });
  };
}
