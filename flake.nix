{
  description = "Maid";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        python = pkgs.python3;
        pythonPackages = python.pkgs;
        
        maid = pkgs.stdenv.mkDerivation {
          pname = "maid";
          version = "0.1.0";
          
          src = self;
          
          nativeBuildInputs = [ python ];
          
          installPhase = ''
            mkdir -p $out/bin
            cp script.py $out/bin/maid
            chmod +x $out/bin/maid

            substituteInPlace $out/bin/maid \
              --replace "#!/usr/bin/env python3" "#!${python}/bin/python3"
          '';
          
          meta = with pkgs.lib; {
            description = "Maid";
            homepage = "https://github.com/uonr/maid";
            license = licenses.mit;
            maintainers = [ ];
            platforms = platforms.darwin;
          };
        };
        
      in
      {
        packages.default = maid;
        packages.maid = maid;
        
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python
            pythonPackages.pip
            pythonPackages.setuptools
            pythonPackages.wheel
          ];
        };
        
        apps.default = {
          type = "app";
          program = "${maid}/bin/maid";
        };
        
        apps.maid = {
          type = "app";
          program = "${maid}/bin/maid";
        };
      });
}
